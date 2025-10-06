import { app, BrowserWindow, Tray, Menu, ipcMain, dialog, shell, globalShortcut, Notification, nativeImage } from 'electron';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import Store from 'electron-store';
import { setupTray, TrayManager } from './tray';
import { setupGlobalShortcuts } from './globalShortcuts';
import { setupNotifications } from './notifications';
import { IconManager } from './iconManager';
import { startupManager } from './startup';
import { createBackgroundMonitor, BackgroundMonitor } from './backgroundMonitor';
import { cleanup } from '@testing-library/react';

interface AppConfig {
  windowBounds?: Electron.Rectangle;
  theme?: 'light' | 'dark' | 'system';
  autoStart?: boolean;
  minimizeToTray?: boolean;
  backendPort?: number;
}

class AIAssistantApp {
  private mainWindow: BrowserWindow | null = null;
  private trayManager: TrayManager | null = null;
  private backendProcess: ChildProcess | null = null;
  private backgroundMonitor: BackgroundMonitor | null = null;
  private store: Store<AppConfig>;
  private isQuitting = false;
  private startedHidden = false;

  constructor() {
    this.store = new Store<AppConfig>({
      defaults: {
        theme: 'system',
        autoStart: true,
        minimizeToTray: true,
        backendPort: 8000
      }
    });

    // Check if started with hidden flag
    const startupArgs = startupManager.handleStartupArgs(process.argv);
    this.startedHidden = startupArgs.hidden;
  }

  async initialize() {
    // Prevent multiple instances
    if (!this.preventMultipleInstances()) {
      return;
    }

    // Handle app events
    app.whenReady().then(() => this.onReady());
    app.on('window-all-closed', () => this.onWindowAllClosed());
    app.on('activate', () => this.onActivate());
    app.on('before-quit', () => this.onBeforeQuit());
    
    // Handle second instance
    app.on('second-instance', () => this.onSecondInstance());

    // Handle system shutdown
    app.on('will-quit', (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        this.gracefulShutdown();
      }
    });
  }

  private async onReady() {
    // Create main window
    await this.createMainWindow();

    // Set up system tray
    this.setupSystemTray();

    // Set up background monitoring
    this.setupBackgroundMonitoring();

    // Set up global shortcuts
    this.setupGlobalShortcuts();

    // Start backend process
    await this.startBackend();

    // Set up auto-start if enabled
    await this.setupAutoStart();

    // Handle startup visibility
    if (this.startedHidden || this.store.get('minimizeToTray')) {
      this.mainWindow?.hide();
      if (process.platform === 'darwin') {
        app.dock.hide();
      }
    }
  }

  private onWindowAllClosed() {
    // On macOS, keep app running even when all windows are closed
    if (process.platform !== 'darwin') {
      if (!this.store.get('minimizeToTray')) {
        app.quit();
      }
    }
  }

  private onActivate() {
    // On macOS, re-create window when dock icon is clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      this.createMainWindow();
    } else if (this.mainWindow) {
      this.mainWindow.show();
      this.mainWindow.focus();
    }
  }

  private onBeforeQuit() {
    this.isQuitting = true;
    
    // Stop background monitoring
    if (this.backgroundMonitor) {
      this.backgroundMonitor.stopMonitoring();
    }
  }

  private onSecondInstance() {
    // Focus existing window if someone tries to run a second instance
    if (this.mainWindow) {
      if (this.mainWindow.isMinimized()) {
        this.mainWindow.restore();
      }
      this.mainWindow.focus();
    }
  }

  private async createMainWindow() {
    const bounds = this.store.get('windowBounds');

    this.mainWindow = new BrowserWindow({
      width: bounds?.width || 1200,
      height: bounds?.height || 800,
      x: bounds?.x,
      y: bounds?.y,
      minWidth: 800,
      minHeight: 600,
      show: !this.startedHidden,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, 'preload.js'),
        webSecurity: true
      },
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      icon: this.getAppIcon()
    });

    // Load the app
    const isDev = process.env.NODE_ENV === 'development';
    if (isDev) {
      this.mainWindow.loadURL('http://localhost:3000');
      this.mainWindow.webContents.openDevTools();
    } else {
      this.mainWindow.loadFile(path.join(__dirname, 'index.html'));
    }

    // Handle window events
    this.mainWindow.on('close', (event) => {
      if (!this.isQuitting && this.store.get('minimizeToTray')) {
        event.preventDefault();
        this.mainWindow?.hide();
        
        if (process.platform === 'darwin') {
          app.dock.hide();
        }
      }
    });

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // Save window bounds
    this.mainWindow.on('resize', () => this.saveWindowBounds());
    this.mainWindow.on('move', () => this.saveWindowBounds());
  }

  private setupSystemTray() {
    if (this.mainWindow) {
      this.trayManager = setupTray(this.mainWindow);
      
      // Update tray icon based on app status
      this.trayManager.updateTrayIcon('idle');
    }
  }

  private setupBackgroundMonitoring() {
    if (this.mainWindow) {
      this.backgroundMonitor = createBackgroundMonitor(this.mainWindow);
      
      // Start monitoring
      this.backgroundMonitor.startMonitoring();
      
      // Listen for monitoring events
      this.backgroundMonitor.on('performance-issues', (issues) => {
        console.log('Performance issues detected:', issues);
        if (this.trayManager) {
          this.trayManager.showNotification(
            'Performance Alert',
            `Detected: ${issues.join(', ')}`
          );
        }
      });

      this.backgroundMonitor.on('proactive-opportunities', (patterns) => {
        console.log('Proactive assistance opportunities:', patterns);
        // Could trigger AI suggestions here
      });

      this.backgroundMonitor.on('user-idle', (idleTime) => {
        console.log(`User idle for ${idleTime}ms`);
        // Could offer to run maintenance tasks
      });
    }
  }

  private setupGlobalShortcuts() {
    // Voice activation shortcut
    globalShortcut.register('CommandOrControl+Shift+V', () => {
      if (this.mainWindow) {
        this.mainWindow.show();
        this.mainWindow.focus();
        this.mainWindow.webContents.send('trigger-voice-command');
      }
    });

    // Quick chat shortcut
    globalShortcut.register('CommandOrControl+Shift+C', () => {
      if (this.mainWindow) {
        this.mainWindow.show();
        this.mainWindow.focus();
        this.mainWindow.webContents.send('focus-chat-input');
      }
    });

    // Toggle window visibility
    globalShortcut.register('CommandOrControl+Shift+A', () => {
      if (this.mainWindow) {
        if (this.mainWindow.isVisible()) {
          this.mainWindow.hide();
        } else {
          this.mainWindow.show();
          this.mainWindow.focus();
        }
      }
    });
  }

  private async setupAutoStart() {
    const autoStartEnabled = this.store.get('autoStart');
    
    if (autoStartEnabled !== undefined) {
      try {
        await startupManager.setupStartup(autoStartEnabled);
      } catch (error) {
        console.error('Failed to setup auto-start:', error);
      }
    }
  }

  private async startBackend() {
    // Backend startup logic would go here
    // This is a placeholder for the Python backend process
    console.log('Backend startup placeholder');
  }

  private saveWindowBounds() {
    if (this.mainWindow) {
      const bounds = this.mainWindow.getBounds();
      this.store.set('windowBounds', bounds);
    }
  }

  private getAppIcon(): string {
    const isDev = process.env.NODE_ENV === 'development';
    const basePath = isDev ? process.cwd() : process.resourcesPath;
    
    switch (process.platform) {
      case 'win32':
        return path.join(basePath, 'assets', 'icons', 'icon.ico');
      case 'darwin':
        return path.join(basePath, 'assets', 'icons', 'icon.icns');
      default:
        return path.join(basePath, 'assets', 'icons', 'icon.png');
    }
  }

  private async gracefulShutdown() {
    console.log('Starting graceful shutdown...');
    
    // Stop background monitoring
    if (this.backgroundMonitor) {
      this.backgroundMonitor.destroy();
    }

    // Destroy tray
    if (this.trayManager) {
      this.trayManager.destroy();
    }

    // Stop backend process
    if (this.backendProcess) {
      this.backendProcess.kill();
    }

    // Unregister global shortcuts
    globalShortcut.unregisterAll();

    // Quit app
    this.isQuitting = true;
    app.quit();
  }

  private preventMultipleInstances(): boolean {
    const gotTheLock = app.requestSingleInstanceLock();

    if (!gotTheLock) {
      app.quit();
      return false;
    }

    return true;
        event.preventDefault();
        this.gracefulShutdown();
      }
    });

    // Setup IPC handlers
    this.setupIpcHandlers();
  }

  private async gracefulShutdown() {
    if (this.isQuitting) return;
    
    this.isQuitting = true;
    console.log('Starting graceful shutdown...');
    
    try {
      await this.cleanup();
      app.quit();
    } catch (error) {
      console.error('Error during graceful shutdown:', error);
      app.quit();
    }
  }

  private async onReady() {
    // Start backend service
    await this.startBackend();

    // Create main window
    this.createMainWindow();

    // Create system tray
    this.createTray();

    // Setup global shortcuts
    this.setupGlobalShortcuts();

    // Setup notifications
    this.setupNotifications();

    // Setup auto-updater
    this.setupAutoUpdater();
  }

  private onWindowAllClosed() {
    if (process.platform !== 'darwin' || this.isQuitting) {
      this.gracefulShutdown();
    }
  }

  private onActivate() {
    if (BrowserWindow.getAllWindows().length === 0) {
      this.createMainWindow();
    } else if (this.mainWindow) {
      this.mainWindow.show();
    }
  }

  private onBeforeQuit() {
    if (!this.isQuitting) {
      this.gracefulShutdown();
    }
  }

  private createMainWindow() {
    const bounds = this.store.get('windowBounds');

    this.mainWindow = new BrowserWindow({
      width: bounds?.width || 1200,
      height: bounds?.height || 800,
      x: bounds?.x,
      y: bounds?.y,
      minWidth: 800,
      minHeight: 600,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, 'preload.js'),
        webSecurity: true
      },
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      show: false,
      icon: this.getAppIcon()
    });

    // Load the app
    if (process.env.NODE_ENV === 'development') {
      this.mainWindow.loadFile(path.join(__dirname, 'index.html'));
      this.mainWindow.webContents.openDevTools();
    } else {
      this.mainWindow.loadFile(path.join(__dirname, 'index.html'));
    }

    // Window events
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow?.show();
    });

    this.mainWindow.on('close', (event) => {
      if (!this.isQuitting && this.store.get('minimizeToTray')) {
        event.preventDefault();
        this.mainWindow?.hide();
      } else {
        this.saveWindowBounds();
      }
    });

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // Save window bounds on resize/move
    this.mainWindow.on('resize', () => this.saveWindowBounds());
    this.mainWindow.on('move', () => this.saveWindowBounds());
  }

  private createTray() {
    // Use the new tray manager
    const trayManager = setupTray(this.mainWindow);
    
    // Setup icon manager with tray manager
    const iconManager = IconManager.getInstance();
    iconManager.setTrayManager(trayManager);
    
    // Store reference for cleanup
    this.tray = trayManager.trayInstance;
  }

  private async startBackend() {
    try {
      const backendPath = path.join(__dirname, '../../backend/main.py');
      const pythonPath = process.platform === 'win32' ? 'python' : 'python3';

      this.backendProcess = spawn(pythonPath, [backendPath], {
        cwd: path.join(__dirname, '../../backend'),
        stdio: ['pipe', 'pipe', 'pipe']
      });

      this.backendProcess.stdout?.on('data', (data) => {
        console.log(`Backend: ${data}`);
      });

      this.backendProcess.stderr?.on('data', (data) => {
        console.error(`Backend Error: ${data}`);
      });

      this.backendProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
        if (code !== 0 && !this.isQuitting) {
          // Try to restart backend
          setTimeout(() => this.startBackend(), 5000);
        }
      });

      // Wait for backend to start
      await new Promise(resolve => setTimeout(resolve, 3000));

    } catch (error) {
      console.error('Failed to start backend:', error);
      dialog.showErrorBox('Backend Error', 'Failed to start AI Assistant backend service.');
    }
  }

  private setupIpcHandlers() {
    // Window controls
    ipcMain.handle('window-minimize', () => {
      this.mainWindow?.minimize();
    });

    ipcMain.handle('window-maximize', () => {
      if (this.mainWindow?.isMaximized()) {
        this.mainWindow.unmaximize();
      } else {
        this.mainWindow?.maximize();
      }
    });

    ipcMain.handle('window-close', () => {
      this.mainWindow?.close();
    });

    // App settings
    ipcMain.handle('get-app-config', () => {
      return this.store.store;
    });

    ipcMain.handle('set-app-config', (_, config: Partial<AppConfig>) => {
      for (const [key, value] of Object.entries(config)) {
        this.store.set(key as keyof AppConfig, value);
      }
    });

    // System info
    ipcMain.handle('get-system-info', () => {
      return {
        platform: process.platform,
        arch: process.arch,
        version: app.getVersion(),
        electronVersion: process.versions.electron,
        nodeVersion: process.versions.node
      };
    });

    // File operations
    ipcMain.handle('show-open-dialog', async (_, options) => {
      const result = await dialog.showOpenDialog(this.mainWindow!, options);
      return result;
    });

    ipcMain.handle('show-save-dialog', async (_, options) => {
      const result = await dialog.showSaveDialog(this.mainWindow!, options);
      return result;
    });

    // External links
    ipcMain.handle('open-external', (_, url: string) => {
      shell.openExternal(url);
    });

    // Service status updates
    ipcMain.on('update-service-status', (_, status) => {
      const iconManager = IconManager.getInstance();
      
      // Determine overall status from service data
      if (status && typeof status === 'object') {
        const services = status.services || status;
        const serviceStatuses = Object.values(services);
        
        // Check if any service is offline or unhealthy
        const hasOffline = serviceStatuses.some((s: any) => s?.status === 'offline');
        const hasUnhealthy = serviceStatuses.some((s: any) => s?.status === 'unhealthy');
        const hasDegraded = serviceStatuses.some((s: any) => s?.status === 'degraded');
        
        if (hasOffline || hasUnhealthy) {
          iconManager.setError();
        } else if (hasDegraded) {
          iconManager.updateStatus('processing'); // Show as processing/warning
        } else {
          iconManager.setIdle();
        }
      }
    });
  }

  private setupAutoUpdater() {
    // Auto-updater implementation would go here
    // For now, just log that it's ready
    console.log('Auto-updater ready');
  }

  private openSettings() {
    // Implementation for settings window
    if (this.mainWindow) {
      this.mainWindow.webContents.send('open-settings');
    }
  }

  private saveWindowBounds() {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.store.set('windowBounds', this.mainWindow.getBounds());
    }
  }

  private getAppIcon(): string {
    const iconName = process.platform === 'win32' ? 'icon.ico' : 
                     process.platform === 'darwin' ? 'icon.icns' : 'icon.png';
    return path.join(__dirname, '../assets', iconName);
  }

  private getTrayIcon(): string {
    const iconName = process.platform === 'win32' ? 'tray-icon.ico' : 
                     process.platform === 'darwin' ? 'tray-iconTemplate.png' : 'tray-icon.png';
    return path.join(__dirname, '../assets', iconName);
  }

  private setupGlobalShortcuts() {
    setupGlobalShortcuts(this.mainWindow);
  }

  private setupNotifications() {
    const notificationManager = setupNotifications();
    
    // Setup icon manager
    const iconManager = IconManager.getInstance();
    iconManager.setNotificationManager(notificationManager);
    
    // Set initial status
    iconManager.setIdle();
  }

  private async cleanup() {
    console.log('Starting application cleanup...');
    
    // Unregister all global shortcuts
    globalShortcut.unregisterAll();

    // Gracefully shutdown backend
    if (this.backendProcess) {
      console.log('Shutting down backend process...');
      
      // Try graceful shutdown first
      this.backendProcess.kill('SIGTERM');
      
      // Wait for graceful shutdown
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          console.log('Backend graceful shutdown timeout, forcing kill...');
          if (this.backendProcess) {
            this.backendProcess.kill('SIGKILL');
          }
          resolve();
        }, 5000);

        this.backendProcess?.on('exit', () => {
          clearTimeout(timeout);
          resolve();
        });
      });
      
      this.backendProcess = null;
    }

    // Cleanup tray
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }

    // Save final state
    this.saveWindowBounds();
    
    console.log('Application cleanup completed');
  }

  private preventMultipleInstances(): boolean {
    const gotTheLock = app.requestSingleInstanceLock();

    if (!gotTheLock) {
      console.log('Another instance is already running');
      app.quit();
      return false;
    }

    app.on('second-instance', () => {
      // Someone tried to run a second instance, focus our window instead
      if (this.mainWindow) {
        if (this.mainWindow.isMinimized()) {
          this.mainWindow.restore();
        }
        this.mainWindow.focus();
      } else {
        this.createMainWindow();
      }
    });

    return true;
  }

  private setupIpcHandlers() {
    // Auto-start management
    ipcMain.handle('app:get-auto-start', async () => {
      return await startupManager.isAutoStartEnabled();
    });

    ipcMain.handle('app:set-auto-start', async (_, enabled: boolean) => {
      const success = await startupManager.setupStartup(enabled);
      if (success) {
        this.store.set('autoStart', enabled);
      }
      return success;
    });

    // Window management
    ipcMain.handle('app:minimize-to-tray', () => {
      if (this.mainWindow) {
        this.mainWindow.hide();
        if (process.platform === 'darwin') {
          app.dock.hide();
        }
      }
    });

    ipcMain.handle('app:show-window', () => {
      if (this.mainWindow) {
        this.mainWindow.show();
        this.mainWindow.focus();
        if (process.platform === 'darwin') {
          app.dock.show();
        }
      }
    });

    // Tray management
    ipcMain.handle('tray:update-icon', (_, status: string) => {
      if (this.trayManager) {
        this.trayManager.updateTrayIcon(status as any);
      }
    });

    ipcMain.handle('tray:show-notification', (_, title: string, body: string) => {
      if (this.trayManager) {
        this.trayManager.showNotification(title, body);
      }
    });

    // Background monitoring
    ipcMain.handle('monitor:get-status', () => {
      return this.backgroundMonitor?.getStats() || null;
    });

    ipcMain.handle('monitor:toggle-proactive', (_, enabled: boolean) => {
      if (this.backgroundMonitor) {
        this.backgroundMonitor.setProactiveAssistance(enabled);
      }
    });

    // App info
    ipcMain.handle('app:get-version', () => {
      return app.getVersion();
    });

    ipcMain.handle('app:get-platform', () => {
      return process.platform;
    });
  }
}

// Create and initialize the app
const aiAssistantApp = new AIAssistantApp();
aiAssistantApp.initialize();

// Initialize and start the application
const aiAssistant = new AIAssistantApp();
aiAssistant.initialize();