/**
 * System Tray Integration for AI Assistant
 */

import { app, Tray, Menu, nativeImage, BrowserWindow } from 'electron';
import * as path from 'path';

export function setupTray(mainWindow: BrowserWindow | null): TrayManager {
  return new TrayManager(mainWindow!);
}

export class TrayManager {
  private tray: Tray | null = null;
  private mainWindow: BrowserWindow | null = null;

  public get trayInstance(): Tray | null {
    return this.tray;
  }

  constructor(mainWindow: BrowserWindow) {
    this.mainWindow = mainWindow;
    this.createTray();
  }

  private createTray(): void {
    // Create tray icon
    const iconPath = this.getTrayIconPath();
    const trayIcon = nativeImage.createFromPath(iconPath);
    
    // Resize icon for tray (16x16 on most platforms)
    const resizedIcon = trayIcon.resize({ width: 16, height: 16 });
    
    this.tray = new Tray(resizedIcon);
    
    // Set tooltip
    this.tray.setToolTip('AI Assistant - Your Personal AI Employee');
    
    // Create context menu
    this.updateContextMenu();
    
    // Handle tray click events
    this.tray.on('click', () => {
      this.toggleWindow();
    });
    
    this.tray.on('right-click', () => {
      if (this.tray) {
        this.tray.popUpContextMenu();
      }
    });
  }

  private getTrayIconPath(): string {
    const isDev = process.env.NODE_ENV === 'development';
    const basePath = isDev ? process.cwd() : process.resourcesPath;
    
    // Platform-specific icon paths
    switch (process.platform) {
      case 'win32':
        return path.join(basePath, 'assets', 'tray-icon.ico');
      case 'darwin':
        return path.join(basePath, 'assets', 'tray-iconTemplate.png');
      default:
        return path.join(basePath, 'assets', 'tray-icon.png');
    }
  }

  private updateContextMenu(): void {
    if (!this.tray) return;

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Show AI Assistant',
        click: () => this.showWindow()
      },
      {
        label: 'Hide AI Assistant',
        click: () => this.hideWindow()
      },
      { type: 'separator' },
      {
        label: 'Voice Command',
        accelerator: 'CmdOrCtrl+Shift+V',
        click: () => this.triggerVoiceCommand()
      },
      {
        label: 'Quick Chat',
        accelerator: 'CmdOrCtrl+Shift+C',
        click: () => this.showQuickChat()
      },
      { type: 'separator' },
      {
        label: 'Settings',
        click: () => this.openSettings()
      },
      {
        label: 'About',
        click: () => this.showAbout()
      },
      { type: 'separator' },
      {
        label: 'Quit AI Assistant',
        accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
        click: () => {
          app.quit();
        }
      }
    ]);

    this.tray.setContextMenu(contextMenu);
  }

  private toggleWindow(): void {
    if (!this.mainWindow) return;

    if (this.mainWindow.isVisible()) {
      this.hideWindow();
    } else {
      this.showWindow();
    }
  }

  private showWindow(): void {
    if (!this.mainWindow) return;

    this.mainWindow.show();
    this.mainWindow.focus();
    
    // Bring to front on macOS
    if (process.platform === 'darwin') {
      app.dock.show();
    }
  }

  private hideWindow(): void {
    if (!this.mainWindow) return;

    this.mainWindow.hide();
    
    // Hide dock icon on macOS when window is hidden
    if (process.platform === 'darwin') {
      app.dock.hide();
    }
  }

  private triggerVoiceCommand(): void {
    // Show window and trigger voice input
    this.showWindow();
    
    // Send message to renderer to start voice recording
    if (this.mainWindow) {
      this.mainWindow.webContents.send('trigger-voice-command');
    }
  }

  private showQuickChat(): void {
    // Create or show a small quick chat window
    this.showWindow();
    
    // Focus on chat input
    if (this.mainWindow) {
      this.mainWindow.webContents.send('focus-chat-input');
    }
  }

  private openSettings(): void {
    this.showWindow();
    
    // Navigate to settings
    if (this.mainWindow) {
      this.mainWindow.webContents.send('open-settings');
    }
  }

  private showAbout(): void {
    // Show about dialog
    const { dialog } = require('electron');
    
    dialog.showMessageBox(this.mainWindow!, {
      type: 'info',
      title: 'About AI Assistant',
      message: 'AI Assistant Desktop',
      detail: `Version: ${app.getVersion()}\n\nYour Personal AI Employee\n\nBuilt with Electron, React, and Python\n\n© 2024 AI Assistant Team`,
      buttons: ['OK']
    });
  }

  public updateTrayIcon(status: 'idle' | 'listening' | 'processing' | 'error' | 'offline'): void {
    if (!this.tray) return;

    // Update tray icon based on status
    let iconName = 'tray-icon';
    if (status !== 'idle') {
      iconName = `tray-icon-${status}`;
    }
    
    const iconPath = this.getTrayIconPath().replace('tray-icon', iconName);
    
    try {
      const icon = nativeImage.createFromPath(iconPath);
      if (!icon.isEmpty()) {
        const resizedIcon = icon.resize({ width: 16, height: 16 });
        this.tray.setImage(resizedIcon);
        
        // Update tooltip based on status
        const statusMessages = {
          idle: 'AI Assistant - Ready',
          listening: 'AI Assistant - Listening...',
          processing: 'AI Assistant - Processing...',
          error: 'AI Assistant - Error',
          offline: 'AI Assistant - Offline'
        };
        
        this.tray.setToolTip(statusMessages[status] || 'AI Assistant');
      }
    } catch (error) {
      console.warn('Failed to update tray icon:', error);
      // Fallback to default icon
      try {
        const defaultIcon = nativeImage.createFromPath(this.getTrayIconPath());
        const resizedIcon = defaultIcon.resize({ width: 16, height: 16 });
        this.tray.setImage(resizedIcon);
      } catch (fallbackError) {
        console.error('Failed to set fallback tray icon:', fallbackError);
      }
    }
  }

  public showNotification(title: string, body: string): void {
    if (!this.tray) return;

    this.tray.displayBalloon({
      title,
      content: body,
      icon: nativeImage.createFromPath(this.getTrayIconPath())
    });
  }

  public destroy(): void {
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }
  }
}