/**
 * Global Keyboard Shortcuts Manager
 */

import { globalShortcut, BrowserWindow } from 'electron';

export interface ShortcutConfig {
  accelerator: string;
  description: string;
  action: () => void;
}

export function setupGlobalShortcuts(mainWindow: BrowserWindow | null): GlobalShortcutsManager {
  return new GlobalShortcutsManager(mainWindow!);
}

export class GlobalShortcutsManager {
  private mainWindow: BrowserWindow;
  private shortcuts: Map<string, ShortcutConfig> = new Map();

  constructor(mainWindow: BrowserWindow) {
    this.mainWindow = mainWindow;
    this.registerDefaultShortcuts();
  }

  private registerDefaultShortcuts(): void {
    // Voice command shortcut
    this.register('voice-command', {
      accelerator: 'CmdOrCtrl+Shift+V',
      description: 'Trigger voice command',
      action: () => this.triggerVoiceCommand()
    });

    // Quick chat shortcut
    this.register('quick-chat', {
      accelerator: 'CmdOrCtrl+Shift+C',
      description: 'Open quick chat',
      action: () => this.openQuickChat()
    });

    // Show/Hide window
    this.register('toggle-window', {
      accelerator: 'CmdOrCtrl+Shift+A',
      description: 'Show/Hide AI Assistant window',
      action: () => this.toggleWindow()
    });

    // Emergency stop
    this.register('emergency-stop', {
      accelerator: 'CmdOrCtrl+Shift+Escape',
      description: 'Emergency stop all automation',
      action: () => this.emergencyStop()
    });

    // Screenshot and analyze
    this.register('screenshot-analyze', {
      accelerator: 'CmdOrCtrl+Shift+S',
      description: 'Take screenshot and analyze',
      action: () => this.screenshotAndAnalyze()
    });

    // Quick automation
    this.register('quick-automation', {
      accelerator: 'CmdOrCtrl+Shift+Q',
      description: 'Quick automation menu',
      action: () => this.showQuickAutomation()
    });
  }

  public register(id: string, config: ShortcutConfig): boolean {
    try {
      // Unregister existing shortcut if it exists
      this.unregister(id);

      // Register new shortcut
      const success = globalShortcut.register(config.accelerator, config.action);
      
      if (success) {
        this.shortcuts.set(id, config);
        console.log(`Registered global shortcut: ${id} (${config.accelerator})`);
      } else {
        console.warn(`Failed to register global shortcut: ${id} (${config.accelerator})`);
      }

      return success;
    } catch (error) {
      console.error(`Error registering shortcut ${id}:`, error);
      return false;
    }
  }

  public unregister(id: string): void {
    const config = this.shortcuts.get(id);
    if (config) {
      globalShortcut.unregister(config.accelerator);
      this.shortcuts.delete(id);
      console.log(`Unregistered global shortcut: ${id}`);
    }
  }

  public unregisterAll(): void {
    globalShortcut.unregisterAll();
    this.shortcuts.clear();
    console.log('Unregistered all global shortcuts');
  }

  public getRegisteredShortcuts(): Array<{ id: string; config: ShortcutConfig }> {
    return Array.from(this.shortcuts.entries()).map(([id, config]) => ({ id, config }));
  }

  public isRegistered(accelerator: string): boolean {
    return globalShortcut.isRegistered(accelerator);
  }

  // Shortcut action implementations
  private triggerVoiceCommand(): void {
    console.log('Global shortcut: Voice command triggered');
    
    // Show window if hidden
    if (!this.mainWindow.isVisible()) {
      this.mainWindow.show();
    }
    
    // Focus window
    this.mainWindow.focus();
    
    // Send message to renderer to start voice recording
    this.mainWindow.webContents.send('global-shortcut', {
      action: 'trigger-voice-command'
    });
  }

  private openQuickChat(): void {
    console.log('Global shortcut: Quick chat triggered');
    
    // Show window if hidden
    if (!this.mainWindow.isVisible()) {
      this.mainWindow.show();
    }
    
    // Focus window
    this.mainWindow.focus();
    
    // Send message to renderer to focus chat input
    this.mainWindow.webContents.send('global-shortcut', {
      action: 'focus-chat-input'
    });
  }

  private toggleWindow(): void {
    console.log('Global shortcut: Toggle window');
    
    if (this.mainWindow.isVisible()) {
      this.mainWindow.hide();
    } else {
      this.mainWindow.show();
      this.mainWindow.focus();
    }
  }

  private emergencyStop(): void {
    console.log('Global shortcut: Emergency stop triggered');
    
    // Send emergency stop signal to renderer
    this.mainWindow.webContents.send('global-shortcut', {
      action: 'emergency-stop'
    });
    
    // Also send to backend via IPC
    this.sendToBackend('emergency-stop', {});
  }

  private screenshotAndAnalyze(): void {
    console.log('Global shortcut: Screenshot and analyze');
    
    // Show window
    if (!this.mainWindow.isVisible()) {
      this.mainWindow.show();
    }
    
    this.mainWindow.focus();
    
    // Trigger screenshot analysis
    this.mainWindow.webContents.send('global-shortcut', {
      action: 'screenshot-analyze'
    });
  }

  private showQuickAutomation(): void {
    console.log('Global shortcut: Quick automation menu');
    
    // Show window
    if (!this.mainWindow.isVisible()) {
      this.mainWindow.show();
    }
    
    this.mainWindow.focus();
    
    // Show quick automation menu
    this.mainWindow.webContents.send('global-shortcut', {
      action: 'show-quick-automation'
    });
  }

  private sendToBackend(action: string, data: any): void {
    // Send message to backend via the renderer process
    this.mainWindow.webContents.send('backend-message', {
      action,
      data
    });
  }

  // Custom shortcut management
  public addCustomShortcut(id: string, accelerator: string, description: string, action: () => void): boolean {
    return this.register(id, {
      accelerator,
      description,
      action
    });
  }

  public removeCustomShortcut(id: string): void {
    this.unregister(id);
  }

  public updateShortcut(id: string, newAccelerator: string): boolean {
    const config = this.shortcuts.get(id);
    if (config) {
      // Create new config with updated accelerator
      const newConfig = {
        ...config,
        accelerator: newAccelerator
      };
      
      // Re-register with new accelerator
      return this.register(id, newConfig);
    }
    return false;
  }

  // Validation helpers
  public validateAccelerator(accelerator: string): boolean {
    try {
      // Try to register a dummy shortcut to validate
      const testResult = globalShortcut.register(accelerator, () => {});
      if (testResult) {
        globalShortcut.unregister(accelerator);
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  public getConflictingShortcut(accelerator: string): string | null {
    for (const [id, config] of this.shortcuts) {
      if (config.accelerator === accelerator) {
        return id;
      }
    }
    return null;
  }
}