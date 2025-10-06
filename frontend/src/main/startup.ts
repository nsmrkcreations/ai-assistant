/**
 * Startup Integration for AI Assistant
 * Handles auto-start functionality across platforms
 */

import { app } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { spawn, exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export class StartupManager {
  private appName = 'AI Assistant';
  private executablePath: string;

  constructor() {
    this.executablePath = process.execPath;
  }

  /**
   * Enable auto-start on system boot
   */
  async enableAutoStart(): Promise<boolean> {
    try {
      switch (process.platform) {
        case 'win32':
          return await this.enableWindowsAutoStart();
        case 'darwin':
          return await this.enableMacAutoStart();
        case 'linux':
          return await this.enableLinuxAutoStart();
        default:
          console.warn('Auto-start not supported on this platform');
          return false;
      }
    } catch (error) {
      console.error('Failed to enable auto-start:', error);
      return false;
    }
  }

  /**
   * Disable auto-start on system boot
   */
  async disableAutoStart(): Promise<boolean> {
    try {
      switch (process.platform) {
        case 'win32':
          return await this.disableWindowsAutoStart();
        case 'darwin':
          return await this.disableMacAutoStart();
        case 'linux':
          return await this.disableLinuxAutoStart();
        default:
          console.warn('Auto-start not supported on this platform');
          return false;
      }
    } catch (error) {
      console.error('Failed to disable auto-start:', error);
      return false;
    }
  }

  /**
   * Check if auto-start is currently enabled
   */
  async isAutoStartEnabled(): Promise<boolean> {
    try {
      switch (process.platform) {
        case 'win32':
          return await this.isWindowsAutoStartEnabled();
        case 'darwin':
          return await this.isMacAutoStartEnabled();
        case 'linux':
          return await this.isLinuxAutoStartEnabled();
        default:
          return false;
      }
    } catch (error) {
      console.error('Failed to check auto-start status:', error);
      return false;
    }
  }

  // Windows implementation
  private async enableWindowsAutoStart(): Promise<boolean> {
    try {
      // Use Windows Registry to add startup entry
      const registryKey = 'HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run';
      const command = `reg add "${registryKey}" /v "${this.appName}" /t REG_SZ /d "\\"${this.executablePath}\\" --hidden" /f`;
      
      await execAsync(command);
      return true;
    } catch (error) {
      console.error('Windows auto-start enable failed:', error);
      return false;
    }
  }

  private async disableWindowsAutoStart(): Promise<boolean> {
    try {
      const registryKey = 'HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run';
      const command = `reg delete "${registryKey}" /v "${this.appName}" /f`;
      
      await execAsync(command);
      return true;
    } catch (error) {
      // It's okay if the key doesn't exist
      return true;
    }
  }

  private async isWindowsAutoStartEnabled(): Promise<boolean> {
    try {
      const registryKey = 'HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run';
      const command = `reg query "${registryKey}" /v "${this.appName}"`;
      
      await execAsync(command);
      return true;
    } catch (error) {
      return false;
    }
  }

  // macOS implementation
  private async enableMacAutoStart(): Promise<boolean> {
    try {
      const plistPath = path.join(
        require('os').homedir(),
        'Library',
        'LaunchAgents',
        'com.aiassistant.desktop.plist'
      );

      const plistContent = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aiassistant.desktop</string>
    <key>ProgramArguments</key>
    <array>
        <string>${this.executablePath}</string>
        <string>--hidden</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>LaunchOnlyOnce</key>
    <true/>
</dict>
</plist>`;

      // Ensure directory exists
      const launchAgentsDir = path.dirname(plistPath);
      if (!fs.existsSync(launchAgentsDir)) {
        fs.mkdirSync(launchAgentsDir, { recursive: true });
      }

      // Write plist file
      fs.writeFileSync(plistPath, plistContent);

      // Load the launch agent
      await execAsync(`launchctl load "${plistPath}"`);
      
      return true;
    } catch (error) {
      console.error('macOS auto-start enable failed:', error);
      return false;
    }
  }

  private async disableMacAutoStart(): Promise<boolean> {
    try {
      const plistPath = path.join(
        require('os').homedir(),
        'Library',
        'LaunchAgents',
        'com.aiassistant.desktop.plist'
      );

      // Unload the launch agent
      try {
        await execAsync(`launchctl unload "${plistPath}"`);
      } catch (error) {
        // It's okay if it's not loaded
      }

      // Remove plist file
      if (fs.existsSync(plistPath)) {
        fs.unlinkSync(plistPath);
      }

      return true;
    } catch (error) {
      console.error('macOS auto-start disable failed:', error);
      return false;
    }
  }

  private async isMacAutoStartEnabled(): Promise<boolean> {
    try {
      const plistPath = path.join(
        require('os').homedir(),
        'Library',
        'LaunchAgents',
        'com.aiassistant.desktop.plist'
      );

      return fs.existsSync(plistPath);
    } catch (error) {
      return false;
    }
  }

  // Linux implementation
  private async enableLinuxAutoStart(): Promise<boolean> {
    try {
      const autostartDir = path.join(
        require('os').homedir(),
        '.config',
        'autostart'
      );

      const desktopFilePath = path.join(autostartDir, 'ai-assistant.desktop');

      const desktopFileContent = `[Desktop Entry]
Type=Application
Name=${this.appName}
Comment=AI Assistant Desktop Application
Exec="${this.executablePath}" --hidden
Icon=ai-assistant
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
Hidden=false`;

      // Ensure directory exists
      if (!fs.existsSync(autostartDir)) {
        fs.mkdirSync(autostartDir, { recursive: true });
      }

      // Write desktop file
      fs.writeFileSync(desktopFilePath, desktopFileContent);
      
      // Make executable
      fs.chmodSync(desktopFilePath, 0o755);

      return true;
    } catch (error) {
      console.error('Linux auto-start enable failed:', error);
      return false;
    }
  }

  private async disableLinuxAutoStart(): Promise<boolean> {
    try {
      const desktopFilePath = path.join(
        require('os').homedir(),
        '.config',
        'autostart',
        'ai-assistant.desktop'
      );

      if (fs.existsSync(desktopFilePath)) {
        fs.unlinkSync(desktopFilePath);
      }

      return true;
    } catch (error) {
      console.error('Linux auto-start disable failed:', error);
      return false;
    }
  }

  private async isLinuxAutoStartEnabled(): Promise<boolean> {
    try {
      const desktopFilePath = path.join(
        require('os').homedir(),
        '.config',
        'autostart',
        'ai-assistant.desktop'
      );

      return fs.existsSync(desktopFilePath);
    } catch (error) {
      return false;
    }
  }

  /**
   * Set up startup integration based on user preferences
   */
  async setupStartup(enabled: boolean): Promise<boolean> {
    if (enabled) {
      return await this.enableAutoStart();
    } else {
      return await this.disableAutoStart();
    }
  }

  /**
   * Handle startup arguments
   */
  handleStartupArgs(argv: string[]): { hidden: boolean; minimized: boolean } {
    const hidden = argv.includes('--hidden') || argv.includes('--startup');
    const minimized = argv.includes('--minimized') || hidden;

    return { hidden, minimized };
  }

  /**
   * Check if app was started at system boot
   */
  isStartedAtBoot(): boolean {
    const args = process.argv;
    return args.includes('--hidden') || args.includes('--startup');
  }
}

export const startupManager = new StartupManager();