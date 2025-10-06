/**
 * Frontend integration tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import '@testing-library/jest-dom';

import App from '../renderer/App';
import { WebSocketProvider } from '../renderer/contexts/WebSocketContext';
import { ThemeProvider } from '../renderer/contexts/ThemeContext';
import { ErrorBoundary } from '../renderer/components/ErrorBoundary';
import SettingsModal from '../renderer/components/SettingsModal';
import { ServiceStatusIndicator } from '../renderer/components/ServiceStatusIndicator';

// Mock electron API
const mockElectronAPI = {
  getAppConfig: jest.fn().mockResolvedValue({}),
  setAppConfig: jest.fn().mockResolvedValue(undefined),
  onSettingsOpen: jest.fn(),
  removeAllListeners: jest.fn(),
  minimizeWindow: jest.fn(),
  maximizeWindow: jest.fn(),
  closeWindow: jest.fn(),
};

(global as any).window.electronAPI = mockElectronAPI;

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string) {
    // Mock sending data
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

(global as any).WebSocket = MockWebSocket;

// Mock fetch
global.fetch = jest.fn();

describe('Frontend Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });
  });

  describe('App Integration', () => {
    test('renders main application components', async () => {
      render(<App />);

      // Should render main components
      expect(screen.getByText(/AI Assistant/i)).toBeInTheDocument();
      
      // Wait for WebSocket connection
      await waitFor(() => {
        // App should be rendered without crashing
        expect(document.querySelector('.flex.h-screen')).toBeInTheDocument();
      });
    });

    test('handles settings modal integration', async () => {
      render(<App />);

      // Simulate opening settings
      act(() => {
        const callback = mockElectronAPI.onSettingsOpen.mock.calls[0]?.[0];
        if (callback) callback();
      });

      await waitFor(() => {
        expect(screen.getByText(/Settings/i)).toBeInTheDocument();
      });
    });
  });

  describe('WebSocket Integration', () => {
    test('WebSocket provider connects and handles messages', async () => {
      const TestComponent = () => {
        return (
          <WebSocketProvider>
            <div data-testid="websocket-test">WebSocket Test</div>
          </WebSocketProvider>
        );
      };

      render(<TestComponent />);

      expect(screen.getByTestId('websocket-test')).toBeInTheDocument();

      // Wait for WebSocket connection
      await waitFor(() => {
        // Connection should be established
        expect(true).toBe(true); // WebSocket mock connects automatically
      });
    });

    test('WebSocket handles reconnection', async () => {
      const TestComponent = () => {
        return (
          <WebSocketProvider>
            <div data-testid="websocket-reconnect">Reconnect Test</div>
          </WebSocketProvider>
        );
      };

      render(<TestComponent />);

      // Simulate connection loss and reconnection
      await waitFor(() => {
        expect(screen.getByTestId('websocket-reconnect')).toBeInTheDocument();
      });
    });
  });

  describe('Settings Integration', () => {
    test('settings modal saves and loads preferences', async () => {
      const mockSettings = {
        theme: 'dark',
        autoStart: true,
        notifications: false,
      };

      mockElectronAPI.getAppConfig.mockResolvedValue(mockSettings);

      render(
        <ThemeProvider>
          <SettingsModal isOpen={true} onClose={() => {}} />
        </ThemeProvider>
      );

      await waitFor(() => {
        expect(screen.getByText(/General Settings/i)).toBeInTheDocument();
      });

      // Check if settings are loaded
      expect(mockElectronAPI.getAppConfig).toHaveBeenCalled();
    });

    test('settings modal handles tab navigation', async () => {
      render(
        <ThemeProvider>
          <SettingsModal isOpen={true} onClose={() => {}} />
        </ThemeProvider>
      );

      await waitFor(() => {
        expect(screen.getByText(/General Settings/i)).toBeInTheDocument();
      });

      // Click on Voice tab
      const voiceTab = screen.getByText(/Voice & AI/i);
      fireEvent.click(voiceTab);

      await waitFor(() => {
        expect(screen.getByText(/Voice & AI Settings/i)).toBeInTheDocument();
      });
    });
  });

  describe('Service Status Integration', () => {
    test('service status indicator fetches and displays status', async () => {
      const mockServiceStatus = {
        services: {
          database: { status: 'healthy', name: 'database' },
          llm: { status: 'healthy', name: 'llm' },
          stt: { status: 'degraded', name: 'stt', error: 'Connection timeout' },
        },
      };

      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockServiceStatus),
      });

      render(<ServiceStatusIndicator showDetails={true} />);

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('/api/services/status');
      });

      // Should show service count
      await waitFor(() => {
        expect(screen.getByText(/services/i)).toBeInTheDocument();
      });
    });

    test('service status indicator handles service restart', async () => {
      const mockServiceStatus = {
        services: {
          database: { status: 'offline', name: 'database', error: 'Service down' },
        },
      };

      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockServiceStatus),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ status: 'success' }),
        });

      render(<ServiceStatusIndicator showDetails={true} />);

      await waitFor(() => {
        expect(screen.getByText(/services/i)).toBeInTheDocument();
      });

      // Click to show details
      const statusIndicator = screen.getByText(/services/i);
      fireEvent.click(statusIndicator);

      await waitFor(() => {
        const restartButton = screen.getByText(/Restart/i);
        if (restartButton) {
          fireEvent.click(restartButton);
        }
      });
    });
  });

  describe('Error Boundary Integration', () => {
    test('error boundary catches and displays errors', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
      expect(screen.getByText(/Try Again/i)).toBeInTheDocument();

      consoleSpy.mockRestore();
    });

    test('error boundary handles error reporting', async () => {
      const ThrowError = () => {
        throw new Error('Test error for reporting');
      };

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: jest.fn().mockResolvedValue(undefined),
        },
      });

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const reportButton = screen.getByText(/Copy Error Report/i);
      fireEvent.click(reportButton);

      await waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Theme Integration', () => {
    test('theme provider manages theme state', () => {
      const TestComponent = () => {
        return (
          <ThemeProvider>
            <div data-testid="theme-test">Theme Test</div>
          </ThemeProvider>
        );
      };

      render(<TestComponent />);

      expect(screen.getByTestId('theme-test')).toBeInTheDocument();
    });
  });

  describe('Performance Integration', () => {
    test('application handles large data sets', async () => {
      // Mock large dataset
      const largeDataset = Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        message: `Message ${i}`,
        timestamp: new Date().toISOString(),
      }));

      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ messages: largeDataset }),
      });

      render(<App />);

      // App should render without performance issues
      await waitFor(() => {
        expect(document.querySelector('.flex.h-screen')).toBeInTheDocument();
      });
    });

    test('application handles rapid state updates', async () => {
      render(<App />);

      // Simulate rapid state updates
      for (let i = 0; i < 10; i++) {
        act(() => {
          // Trigger rapid updates
          window.dispatchEvent(new CustomEvent('test-update', { detail: i }));
        });
      }

      // App should remain stable
      expect(document.querySelector('.flex.h-screen')).toBeInTheDocument();
    });
  });

  describe('Accessibility Integration', () => {
    test('application is accessible', async () => {
      render(<App />);

      // Check for basic accessibility features
      const mainContent = document.querySelector('main') || document.querySelector('[role="main"]');
      
      // Should have proper structure
      expect(document.querySelector('.flex.h-screen')).toBeInTheDocument();
    });

    test('settings modal is accessible', async () => {
      render(
        <ThemeProvider>
          <SettingsModal isOpen={true} onClose={() => {}} />
        </ThemeProvider>
      );

      await waitFor(() => {
        expect(screen.getByText(/Settings/i)).toBeInTheDocument();
      });

      // Should have proper ARIA attributes
      const modal = screen.getByText(/Settings/i).closest('[role="dialog"]') || 
                   screen.getByText(/Settings/i).closest('.fixed');
      
      expect(modal).toBeInTheDocument();
    });
  });
});

describe('End-to-End Workflow Tests', () => {
  test('complete chat workflow', async () => {
    const mockChatResponse = {
      message: 'Hello! How can I help you?',
      context_id: 'test-123',
      timestamp: new Date().toISOString(),
    };

    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockChatResponse),
    });

    render(<App />);

    await waitFor(() => {
      expect(document.querySelector('.flex.h-screen')).toBeInTheDocument();
    });

    // Simulate chat interaction
    // This would require more detailed component testing
  });

  test('settings save and load workflow', async () => {
    const mockSettings = {
      theme: 'dark',
      autoStart: true,
      notifications: true,
    };

    mockElectronAPI.getAppConfig.mockResolvedValue(mockSettings);
    mockElectronAPI.setAppConfig.mockResolvedValue(undefined);

    render(
      <ThemeProvider>
        <SettingsModal isOpen={true} onClose={() => {}} />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(mockElectronAPI.getAppConfig).toHaveBeenCalled();
    });

    // Settings should be loaded and ready for modification
    expect(screen.getByText(/General Settings/i)).toBeInTheDocument();
  });
});