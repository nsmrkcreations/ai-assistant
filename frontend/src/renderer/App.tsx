import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';
import StatusBar from './components/StatusBar';
import SettingsModal from './components/SettingsModal';
import DemoMode from './components/DemoMode';
import VoiceInterface from './components/VoiceInterface';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ThemeProvider } from './contexts/ThemeContext';
import { WebSocketProvider, useWebSocket } from './contexts/WebSocketContext';
import { useVoiceActivation } from './hooks/useVoiceActivation';
import { useSystemStatus } from './hooks/useSystemStatus';

const AppContent: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const { systemStatus, isConnected } = useSystemStatus();
  const { sendMessage } = useWebSocket();

  // Voice activation hotkey
  useVoiceActivation({
    onActivate: () => {
      if (voiceEnabled) {
        setVoiceMode(true);
      }
    },
    hotkey: 'ctrl+shift+v',

  });

  const handleVoiceTranscription = async (text: string) => {
    setVoiceMode(false);
    if (text.trim()) {
      try {
        await sendMessage({
          message: text,
          include_audio: false,
          context_id: null
        });
      } catch (error) {
        console.error('Failed to send voice message:', error);
      }
    }
  };

  const handleVoiceError = (error: string) => {
    console.error('Voice error:', error);
    setVoiceMode(false);
  };

  useEffect(() => {
    // Listen for settings open event from main process
    window.electronAPI?.onSettingsOpen(() => {
      setSettingsOpen(true);
    });

    // Check if this is first run to show demo
    const checkFirstRun = async () => {
      try {
        const config = await window.electronAPI?.getAppConfig();
        if (!config?.hasSeenDemo) {
          setDemoMode(true);
        }
      } catch (error) {
        console.error('Error checking first run:', error);
      }
    };

    checkFirstRun();

    return () => {
      window.electronAPI?.removeAllListeners('open-settings');
    };
  }, []);

  const handleDemoComplete = async () => {
    setDemoMode(false);
    try {
      await window.electronAPI?.setAppConfig({ hasSeenDemo: true });
    } catch (error) {
      console.error('Error saving demo completion:', error);
    }
  };

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <WebSocketProvider>
          <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          {/* Sidebar */}
          <Sidebar 
            isOpen={sidebarOpen} 
            onClose={() => setSidebarOpen(false)}
            onOpenSettings={() => setSettingsOpen(true)}
          />

          {/* Main Content */}
          <div className="flex-1 flex flex-col">
            {/* Title Bar (Windows/Linux) */}
            {process.platform !== 'darwin' && (
              <div className="h-8 bg-gray-100 dark:bg-gray-800 flex items-center justify-between px-4 drag-region">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setSidebarOpen(!sidebarOpen)}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded no-drag"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                  </button>
                  <span className="text-sm font-medium">AI Assistant</span>
                </div>
                
                <div className="flex items-center space-x-1 no-drag">
                  <button
                    onClick={() => window.electronAPI?.minimizeWindow()}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                    </svg>
                  </button>
                  <button
                    onClick={() => window.electronAPI?.maximizeWindow()}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4h16v16H4z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => window.electronAPI?.closeWindow()}
                    className="p-1 hover:bg-red-500 hover:text-white rounded"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            )}

            {/* Chat Interface */}
            <div className="flex-1 overflow-hidden relative">
              <ChatInterface />
              
              {/* Voice Interface Overlay */}
              {voiceMode && (
                <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-xl">
                    <VoiceInterface
                      onTranscription={handleVoiceTranscription}
                      onError={handleVoiceError}
                    />
                    <button
                      onClick={() => setVoiceMode(false)}
                      className="mt-4 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Status Bar */}
            <StatusBar 
              systemStatus={systemStatus}
              isConnected={isConnected}
            />
          </div>

          {/* Modals */}
          {settingsOpen && (
            <SettingsModal 
              isOpen={settingsOpen}
              onClose={() => setSettingsOpen(false)}
            />
          )}

          {demoMode && (
            <DemoMode 
              isOpen={demoMode}
              onComplete={handleDemoComplete}
            />
          )}
          </div>
        </WebSocketProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <WebSocketProvider>
          <AppContent />
        </WebSocketProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;