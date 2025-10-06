import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { Settings, Mic, Shield, Keyboard, Bell, Puzzle, Database, RotateCcw, Save, X } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState('general');
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    autoStart: true,
    minimizeToTray: true,
    notifications: true,
    voiceActivation: false,
    llmModel: 'llama3.1:8b',
    sttModel: 'base',
    ttsVoice: 'en_US-lessac-medium',
    ttsSpeed: 1.0,
    autoUpdate: true,
    enableLearning: true,
    enableAutomation: true,
    confirmActions: true,
    safetyMode: true,
    globalShortcuts: {
      voiceCommand: 'CmdOrCtrl+Shift+V',
      quickChat: 'CmdOrCtrl+Shift+C',
      toggleWindow: 'CmdOrCtrl+Shift+A',
      emergencyStop: 'CmdOrCtrl+Shift+Escape'
    },
    plugins: {
      enabled: true,
      autoUpdate: false
    },
    database: {
      retentionDays: 30,
      autoCleanup: true
    },
    recovery: {
      enabled: true,
      maxAttempts: 3
    }
  });

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    try {
      const config = await window.electronAPI?.getAppConfig();
      if (config) {
        setSettings(prev => ({ ...prev, ...config }));
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      await window.electronAPI?.setAppConfig(settings);
      setHasChanges(false);
      // Send settings update to backend
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!response.ok) {
        throw new Error('Failed to save settings to backend');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const resetToDefaults = () => {
    setSettings({
      autoStart: true,
      minimizeToTray: true,
      notifications: true,
      voiceActivation: false,
      llmModel: 'llama3.1:8b',
      sttModel: 'base',
      ttsVoice: 'en_US-lessac-medium',
      ttsSpeed: 1.0,
      autoUpdate: true,
      enableLearning: true,
      enableAutomation: true,
      confirmActions: true,
      safetyMode: true,
      globalShortcuts: {
        voiceCommand: 'CmdOrCtrl+Shift+V',
        quickChat: 'CmdOrCtrl+Shift+C',
        toggleWindow: 'CmdOrCtrl+Shift+A',
        emergencyStop: 'CmdOrCtrl+Shift+Escape'
      },
      plugins: {
        enabled: true,
        autoUpdate: false
      },
      database: {
        retentionDays: 30,
        autoCleanup: true
      },
      recovery: {
        enabled: true,
        maxAttempts: 3
      }
    });
    setHasChanges(true);
  };

  if (!isOpen) return null;

  const tabs = [
    { id: 'general', label: 'General', icon: Settings },
    { id: 'voice', label: 'Voice & AI', icon: Mic },
    { id: 'automation', label: 'Automation', icon: Shield },
    { id: 'shortcuts', label: 'Shortcuts', icon: Keyboard },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'plugins', label: 'Plugins', icon: Puzzle },
    { id: 'data', label: 'Data & Storage', icon: Database },
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-5xl h-4/5 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Settings</h2>
          <div className="flex items-center space-x-2">
            {hasChanges && (
              <>
                <button
                  onClick={resetToDefaults}
                  className="flex items-center space-x-1 px-3 py-1 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <RotateCcw size={16} />
                  <span>Reset</span>
                </button>
                <button
                  onClick={saveSettings}
                  disabled={saving}
                  className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  <Save size={16} />
                  <span>{saving ? 'Saving...' : 'Save'}</span>
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-1/4 bg-gray-50 dark:bg-gray-900 p-4 overflow-y-auto">
            <nav className="space-y-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left transition-colors ${activeTab === tab.id
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                      }`}
                  >
                    <Icon size={18} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {activeTab === 'general' && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">General Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Theme
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Choose your preferred theme
                      </p>
                    </div>
                    <select
                      value={theme}
                      onChange={(e) => setTheme(e.target.value as any)}
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="system">System</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Auto Start
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Start AI Assistant when system boots
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.autoStart}
                      onChange={(e) => handleSettingChange('autoStart', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Minimize to Tray
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Keep running in system tray when closed
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.minimizeToTray}
                      onChange={(e) => handleSettingChange('minimizeToTray', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Auto Updates
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Automatically download and install updates
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.autoUpdate}
                      onChange={(e) => handleSettingChange('autoUpdate', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'voice' && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Voice & AI Settings</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Language Model
                    </label>
                    <select
                      value={settings.llmModel}
                      onChange={(e) => handleSettingChange('llmModel', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="llama3.1:8b">Llama 3.1 8B</option>
                      <option value="llama3.1:70b">Llama 3.1 70B</option>
                      <option value="mistral:7b">Mistral 7B</option>
                      <option value="codellama:7b">CodeLlama 7B</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Speech Recognition Model
                    </label>
                    <select
                      value={settings.sttModel}
                      onChange={(e) => handleSettingChange('sttModel', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="tiny">Tiny (fastest)</option>
                      <option value="base">Base (balanced)</option>
                      <option value="small">Small (better quality)</option>
                      <option value="medium">Medium (high quality)</option>
                      <option value="large">Large (best quality)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Text-to-Speech Voice
                    </label>
                    <select
                      value={settings.ttsVoice}
                      onChange={(e) => handleSettingChange('ttsVoice', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="en_US-lessac-medium">Lessac (US English, Female)</option>
                      <option value="en_US-amy-medium">Amy (US English, Female)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Voice Speed: {settings.ttsSpeed}x
                    </label>
                    <input
                      type="range"
                      min="0.5"
                      max="2.0"
                      step="0.1"
                      value={settings.ttsSpeed}
                      onChange={(e) => handleSettingChange('ttsSpeed', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Voice Activation
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Enable voice activation detection
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.voiceActivation}
                      onChange={(e) => handleSettingChange('voiceActivation', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'automation' && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Automation Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Enable Automation
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Allow AI to perform system and application automation
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.enableAutomation}
                      onChange={(e) => handleSettingChange('enableAutomation', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Confirm Actions
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Ask for confirmation before performing potentially dangerous actions
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.confirmActions}
                      onChange={(e) => handleSettingChange('confirmActions', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Safety Mode
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Restrict access to sensitive system functions
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.safetyMode}
                      onChange={(e) => handleSettingChange('safetyMode', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'shortcuts' && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Global Shortcuts</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Voice Command
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Trigger voice input from anywhere
                      </p>
                    </div>
                    <input
                      type="text"
                      value={settings.globalShortcuts.voiceCommand}
                      onChange={(e) => handleSettingChange('globalShortcuts', {
                        ...settings.globalShortcuts,
                        voiceCommand: e.target.value
                      })}
                      className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Quick Chat
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Open quick chat window
                      </p>
                    </div>
                    <input
                      type="text"
                      value={settings.globalShortcuts.quickChat}
                      onChange={(e) => handleSettingChange('globalShortcuts', {
                        ...settings.globalShortcuts,
                        quickChat: e.target.value
                      })}
                      className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Toggle Window
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Show/hide main window
                      </p>
                    </div>
                    <input
                      type="text"
                      value={settings.globalShortcuts.toggleWindow}
                      onChange={(e) => handleSettingChange('globalShortcuts', {
                        ...settings.globalShortcuts,
                        toggleWindow: e.target.value
                      })}
                      className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Emergency Stop
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Stop all automation immediately
                      </p>
                    </div>
                    <input
                      type="text"
                      value={settings.globalShortcuts.emergencyStop}
                      onChange={(e) => handleSettingChange('globalShortcuts', {
                        ...settings.globalShortcuts,
                        emergencyStop: e.target.value
                      })}
                      className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Notification Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Enable Notifications
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Show desktop notifications
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.notifications}
                      onChange={(e) => handleSettingChange('notifications', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'plugins' && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Plugin Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Enable Plugins
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Allow third-party plugins to extend functionality
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.plugins.enabled}
                      onChange={(e) => handleSettingChange('plugins', {
                        ...settings.plugins,
                        enabled: e.target.checked
                      })}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Auto-update Plugins
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Automatically update plugins when available
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.plugins.autoUpdate}
                      onChange={(e) => handleSettingChange('plugins', {
                        ...settings.plugins,
                        autoUpdate: e.target.checked
                      })}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'data' && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Data & Storage Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Data Retention (Days)
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        How long to keep chat history and logs
                      </p>
                    </div>
                    <input
                      type="number"
                      min="1"
                      max="365"
                      value={settings.database.retentionDays}
                      onChange={(e) => handleSettingChange('database', {
                        ...settings.database,
                        retentionDays: parseInt(e.target.value)
                      })}
                      className="w-20 px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Auto Cleanup
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Automatically clean up old data
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.database.autoCleanup}
                      onChange={(e) => handleSettingChange('database', {
                        ...settings.database,
                        autoCleanup: e.target.checked
                      })}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Learning & Personalization
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Learn from your usage patterns to improve suggestions
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.enableLearning}
                      onChange={(e) => handleSettingChange('enableLearning', e.target.checked)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Auto Recovery
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Automatically recover from service failures
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.recovery.enabled}
                      onChange={(e) => handleSettingChange('recovery', {
                        ...settings.recovery,
                        enabled: e.target.checked
                      })}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Max Recovery Attempts
                      </label>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Maximum attempts before giving up
                      </p>
                    </div>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={settings.recovery.maxAttempts}
                      onChange={(e) => handleSettingChange('recovery', {
                        ...settings.recovery,
                        maxAttempts: parseInt(e.target.value)
                      })}
                      className="w-20 px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;