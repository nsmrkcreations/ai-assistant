/**
 * Preload script for AI Assistant
 * Exposes secure APIs to the renderer process
 */

import { contextBridge, ipcRenderer } from 'electron';

// Define the API interface
interface ElectronAPI {
  // App management
  app: {
    getVersion: () => Promise<string>;
    getPlatform: () => Promise<string>;
    getAutoStart: () => Promise<boolean>;
    setAutoStart: (enabled: boolean) => Promise<boolean>;
    minimizeToTray: () => Promise<void>;
    showWindow: () => Promise<void>;
    quit: () => void;
  };

  // File system operations
  file: {
    openDialog: (options?: Electron.OpenDialogOptions) => Promise<string[] | null>;
    saveDialog: (options?: Electron.SaveDialogOptions) => Promise<string | null>;
    read: (filePath: string) => Promise<{ success: boolean; content?: string; error?: string }>;
    write: (filePath: string, content: string) => Promise<{ success: boolean; error?: string }>;
    exists: (filePath: string) => Promise<boolean>;
    getInfo: (filePath: string) => Promise<{ success: boolean; info?: any; error?: string }>;
    showInFolder: (filePath: string) => Promise<{ success: boolean; error?: string }>;
    openExternal: (filePath: string) => Promise<{ success: boolean; error?: string }>;
    getRecent: () => Promise<string[]>;
    clearRecent: () => Promise<{ success: boolean }>;
    listDirectory: (dirPath: string) => Promise<{ success: boolean; items?: any[]; error?: string }>;
    watchDirectory: (dirPath: string) => Promise<{ success: boolean; error?: string }>;
    unwatchDirectory: (dirPath: string) => Promise<{ success: boolean }>;
  };

  // Tray operations
  tray: {
    updateIcon: (status: string) => Promise<void>;
    showNotification: (title: string, body: string) => Promise<void>;
  };

  // Background monitoring
  monitor: {
    getStatus: () => Promise<any>;
    toggleProactive: (enabled: boolean) => Promise<void>;
  };

  // Event listeners
  on: (channel: string, callback: (...args: any[]) => void) => void;
  off: (channel: string, callback: (...args: any[]) => void) => void;
  
  // File drop handler
  onFilesDropped?: (files: Array<{ name: string; path: string; size: number; type: string }>) => void;
}

// Expose the API to the renderer process
const electronAPI: ElectronAPI = {
  app: {
    getVersion: () => ipcRenderer.invoke('app:get-version'),
    getPlatform: () => ipcRenderer.invoke('app:get-platform'),
    getAutoStart: () => ipcRenderer.invoke('app:get-auto-start'),
    setAutoStart: (enabled: boolean) => ipcRenderer.invoke('app:set-auto-start', enabled),
    minimizeToTray: () => ipcRenderer.invoke('app:minimize-to-tray'),
    showWindow: () => ipcRenderer.invoke('app:show-window'),
    quit: () => ipcRenderer.send('app:quit')
  },

  file: {
    openDialog: (options) => ipcRenderer.invoke('file:open-dialog', options),
    saveDialog: (options) => ipcRenderer.invoke('file:save-dialog', options),
    read: (filePath) => ipcRenderer.invoke('file:read', filePath),
    write: (filePath, content) => ipcRenderer.invoke('file:write', filePath, content),
    exists: (filePath) => ipcRenderer.invoke('file:exists', filePath),
    getInfo: (filePath) => ipcRenderer.invoke('file:get-info', filePath),
    showInFolder: (filePath) => ipcRenderer.invoke('file:show-in-folder', filePath),
    openExternal: (filePath) => ipcRenderer.invoke('file:open-external', filePath),
    getRecent: () => ipcRenderer.invoke('file:get-recent'),
    clearRecent: () => ipcRenderer.invoke('file:clear-recent'),
    listDirectory: (dirPath) => ipcRenderer.invoke('file:list-directory', dirPath),
    watchDirectory: (dirPath) => ipcRenderer.invoke('file:watch-directory', dirPath),
    unwatchDirectory: (dirPath) => ipcRenderer.invoke('file:unwatch-directory', dirPath)
  },

  tray: {
    updateIcon: (status) => ipcRenderer.invoke('tray:update-icon', status),
    showNotification: (title, body) => ipcRenderer.invoke('tray:show-notification', title, body)
  },

  monitor: {
    getStatus: () => ipcRenderer.invoke('monitor:get-status'),
    toggleProactive: (enabled) => ipcRenderer.invoke('monitor:toggle-proactive', enabled)
  },

  on: (channel: string, callback: (...args: any[]) => void) => {
    // Whitelist of allowed channels
    const allowedChannels = [
      'trigger-voice-command',
      'focus-chat-input',
      'open-settings',
      'file:directory-changed',
      'file:system-open',
      'protocol:url-opened',
      'performance-suggestions',
      'system-metrics',
      'user-activity',
      'proactive-opportunities'
    ];

    if (allowedChannels.includes(channel)) {
      ipcRenderer.on(channel, callback);
    }
  },

  off: (channel: string, callback: (...args: any[]) => void) => {
    ipcRenderer.off(channel, callback);
  }
};

// Expose the API
contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// Also expose a simplified version for backward compatibility
contextBridge.exposeInMainWorld('electron', {
  ipcRenderer: {
    invoke: (channel: string, ...args: any[]) => {
      // Only allow specific channels for security
      const allowedChannels = [
        'app:get-version',
        'app:get-platform',
        'app:get-auto-start',
        'app:set-auto-start',
        'app:minimize-to-tray',
        'app:show-window',
        'file:open-dialog',
        'file:save-dialog',
        'file:read',
        'file:write',
        'file:exists',
        'file:get-info',
        'file:show-in-folder',
        'file:open-external',
        'file:get-recent',
        'file:clear-recent',
        'file:list-directory',
        'file:watch-directory',
        'file:unwatch-directory',
        'tray:update-icon',
        'tray:show-notification',
        'monitor:get-status',
        'monitor:toggle-proactive'
      ];

      if (allowedChannels.includes(channel)) {
        return ipcRenderer.invoke(channel, ...args);
      }
    },
    
    on: (channel: string, callback: (...args: any[]) => void) => {
      const allowedChannels = [
        'trigger-voice-command',
        'focus-chat-input',
        'open-settings',
        'file:directory-changed',
        'file:system-open',
        'protocol:url-opened',
        'performance-suggestions'
      ];

      if (allowedChannels.includes(channel)) {
        ipcRenderer.on(channel, callback);
      }
    },

    off: (channel: string, callback: (...args: any[]) => void) => {
      ipcRenderer.off(channel, callback);
    }
  }
});

// Type declarations for TypeScript
declare global {
  interface Window {
    electronAPI: ElectronAPI;
    electron: {
      ipcRenderer: {
        invoke: (channel: string, ...args: any[]) => Promise<any>;
        on: (channel: string, callback: (...args: any[]) => void) => void;
        off: (channel: string, callback: (...args: any[]) => void) => void;
      };
    };
  }
}