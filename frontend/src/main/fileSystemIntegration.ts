/**
 * File System Integration for AI Assistant
 * Handles drag-drop, file associations, and native file operations
 */

import { app, dialog, shell, BrowserWindow, ipcMain, protocol } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { EventEmitter } from 'events';

export interface FileOperation {
  type: 'open' | 'save' | 'create' | 'delete' | 'move' | 'copy';
  source?: string;
  destination?: string;
  content?: string;
  filters?: Electron.FileFilter[];
}

export class FileSystemIntegration extends EventEmitter {
  private mainWindow: BrowserWindow | null = null;
  private watchedDirectories: Map<string, fs.FSWatcher> = new Map();
  private recentFiles: string[] = [];
  private maxRecentFiles = 10;

  constructor(mainWindow: BrowserWindow) {
    super();
    this.mainWindow = mainWindow;
    this.setupFileProtocol();
    this.setupIpcHandlers();
    this.setupDragAndDrop();
    this.loadRecentFiles();
  }

  /**
   * Set up custom file protocol for secure file access
   */
  private setupFileProtocol(): void {
    protocol.registerFileProtocol('ai-assistant-file', (request, callback) => {
      const filePath = request.url.replace('ai-assistant-file://', '');
      
      // Security check - only allow access to user's documents and downloads
      const userHome = require('os').homedir();
      const allowedPaths = [
        path.join(userHome, 'Documents'),
        path.join(userHome, 'Downloads'),
        path.join(userHome, 'Desktop')
      ];

      const isAllowed = allowedPaths.some(allowedPath => 
        filePath.startsWith(allowedPath)
      );

      if (isAllowed && fs.existsSync(filePath)) {
        callback({ path: filePath });
      } else {
        callback({ error: -6 }); // FILE_NOT_FOUND
      }
    });
  }

  /**
   * Set up IPC handlers for file operations
   */
  private setupIpcHandlers(): void {
    // File dialog operations
    ipcMain.handle('file:open-dialog', async (_, options: Electron.OpenDialogOptions) => {
      if (!this.mainWindow) return null;

      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openFile', 'multiSelections'],
        filters: [
          { name: 'All Files', extensions: ['*'] },
          { name: 'Documents', extensions: ['pdf', 'doc', 'docx', 'txt', 'rtf'] },
          { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'] },
          { name: 'Audio', extensions: ['mp3', 'wav', 'ogg', 'flac', 'm4a'] },
          { name: 'Video', extensions: ['mp4', 'avi', 'mkv', 'mov', 'wmv'] },
          ...options.filters || []
        ],
        ...options
      });

      if (!result.canceled && result.filePaths.length > 0) {
        // Add to recent files
        result.filePaths.forEach(filePath => this.addToRecentFiles(filePath));
        return result.filePaths;
      }

      return null;
    });

    ipcMain.handle('file:save-dialog', async (_, options: Electron.SaveDialogOptions) => {
      if (!this.mainWindow) return null;

      const result = await dialog.showSaveDialog(this.mainWindow, {
        filters: [
          { name: 'All Files', extensions: ['*'] },
          { name: 'Text Files', extensions: ['txt'] },
          { name: 'JSON Files', extensions: ['json'] },
          { name: 'CSV Files', extensions: ['csv'] },
          ...options.filters || []
        ],
        ...options
      });

      if (!result.canceled && result.filePath) {
        return result.filePath;
      }

      return null;
    });

    // File operations
    ipcMain.handle('file:read', async (_, filePath: string) => {
      try {
        if (!this.isPathAllowed(filePath)) {
          throw new Error('Access denied to file path');
        }

        const content = fs.readFileSync(filePath, 'utf-8');
        this.addToRecentFiles(filePath);
        return { success: true, content };
      } catch (error) {
        return { success: false, error: (error as Error).message };
      }
    });

    ipcMain.handle('file:write', async (_, filePath: string, content: string) => {
      try {
        if (!this.isPathAllowed(filePath)) {
          throw new Error('Access denied to file path');
        }

        // Ensure directory exists
        const dir = path.dirname(filePath);
        if (!fs.existsSync(dir)) {
          fs.mkdirSync(dir, { recursive: true });
        }

        fs.writeFileSync(filePath, content, 'utf-8');
        this.addToRecentFiles(filePath);
        return { success: true };
      } catch (error) {
        return { success: false, error: (error as Error).message };
      }
    });

    ipcMain.handle('file:exists', async (_, filePath: string) => {
      try {
        return fs.existsSync(filePath);
      } catch (error) {
        return false;
      }
    });

    ipcMain.handle('file:get-info', async (_, filePath: string) => {
      try {
        if (!this.isPathAllowed(filePath)) {
          throw new Error('Access denied to file path');
        }

        const stats = fs.statSync(filePath);
        return {
          success: true,
          info: {
            size: stats.size,
            created: stats.birthtime,
            modified: stats.mtime,
            isDirectory: stats.isDirectory(),
            isFile: stats.isFile()
          }
        };
      } catch (error) {
        return { success: false, error: (error as Error).message };
      }
    });

    ipcMain.handle('file:show-in-folder', async (_, filePath: string) => {
      try {
        shell.showItemInFolder(filePath);
        return { success: true };
      } catch (error) {
        return { success: false, error: (error as Error).message };
      }
    });

    ipcMain.handle('file:open-external', async (_, filePath: string) => {
      try {
        await shell.openPath(filePath);
        return { success: true };
      } catch (error) {
        return { success: false, error: (error as Error).message };
      }
    });

    // Recent files
    ipcMain.handle('file:get-recent', () => {
      return this.recentFiles;
    });

    ipcMain.handle('file:clear-recent', () => {
      this.recentFiles = [];
      this.saveRecentFiles();
      return { success: true };
    });

    // Directory operations
    ipcMain.handle('file:list-directory', async (_, dirPath: string) => {
      try {
        if (!this.isPathAllowed(dirPath)) {
          throw new Error('Access denied to directory path');
        }

        const items = fs.readdirSync(dirPath).map(item => {
          const itemPath = path.join(dirPath, item);
          const stats = fs.statSync(itemPath);
          
          return {
            name: item,
            path: itemPath,
            isDirectory: stats.isDirectory(),
            size: stats.size,
            modified: stats.mtime
          };
        });

        return { success: true, items };
      } catch (error) {
        return { success: false, error: (error as Error).message };
      }
    });

    // File watching
    ipcMain.handle('file:watch-directory', async (_, dirPath: string) => {
      try {
        if (!this.isPathAllowed(dirPath)) {
          throw new Error('Access denied to directory path');
        }

        if (this.watchedDirectories.has(dirPath)) {
          return { success: true, message: 'Already watching directory' };
        }

        const watcher = fs.watch(dirPath, { recursive: true }, (eventType, filename) => {
          if (filename && this.mainWindow) {
            this.mainWindow.webContents.send('file:directory-changed', {
              directory: dirPath,
              eventType,
              filename: path.join(dirPath, filename)
            });
          }
        });

        this.watchedDirectories.set(dirPath, watcher);
        return { success: true };
      } catch (error) {
        return { success: false, error: (error as Error).message };
      }
    });

    ipcMain.handle('file:unwatch-directory', async (_, dirPath: string) => {
      const watcher = this.watchedDirectories.get(dirPath);
      if (watcher) {
        watcher.close();
        this.watchedDirectories.delete(dirPath);
      }
      return { success: true };
    });
  }

  /**
   * Set up drag and drop functionality
   */
  private setupDragAndDrop(): void {
    if (!this.mainWindow) return;

    // Handle file drops
    this.mainWindow.webContents.on('dom-ready', () => {
      if (!this.mainWindow) return;

      // Inject drag and drop handling
      this.mainWindow.webContents.executeJavaScript(`
        document.addEventListener('dragover', (e) => {
          e.preventDefault();
          e.stopPropagation();
        });

        document.addEventListener('drop', (e) => {
          e.preventDefault();
          e.stopPropagation();
          
          const files = Array.from(e.dataTransfer.files).map(file => ({
            name: file.name,
            path: file.path,
            size: file.size,
            type: file.type
          }));
          
          if (files.length > 0) {
            window.electronAPI?.onFilesDropped?.(files);
          }
        });
      `);
    });
  }

  /**
   * Check if file path is allowed for security
   */
  private isPathAllowed(filePath: string): boolean {
    const userHome = require('os').homedir();
    const allowedPaths = [
      path.join(userHome, 'Documents'),
      path.join(userHome, 'Downloads'),
      path.join(userHome, 'Desktop'),
      path.join(userHome, 'Pictures'),
      path.join(userHome, 'Music'),
      path.join(userHome, 'Videos')
    ];

    // Also allow temporary directories
    const tempDir = require('os').tmpdir();
    allowedPaths.push(tempDir);

    return allowedPaths.some(allowedPath => 
      filePath.startsWith(allowedPath)
    );
  }

  /**
   * Add file to recent files list
   */
  private addToRecentFiles(filePath: string): void {
    // Remove if already exists
    const index = this.recentFiles.indexOf(filePath);
    if (index > -1) {
      this.recentFiles.splice(index, 1);
    }

    // Add to beginning
    this.recentFiles.unshift(filePath);

    // Limit size
    if (this.recentFiles.length > this.maxRecentFiles) {
      this.recentFiles = this.recentFiles.slice(0, this.maxRecentFiles);
    }

    // Save to storage
    this.saveRecentFiles();

    // Emit event
    this.emit('recent-files-updated', this.recentFiles);
  }

  /**
   * Load recent files from storage
   */
  private loadRecentFiles(): void {
    try {
      const Store = require('electron-store');
      const store = new Store();
      this.recentFiles = store.get('recentFiles', []);
      
      // Filter out files that no longer exist
      this.recentFiles = this.recentFiles.filter(filePath => 
        fs.existsSync(filePath)
      );
    } catch (error) {
      console.error('Failed to load recent files:', error);
      this.recentFiles = [];
    }
  }

  /**
   * Save recent files to storage
   */
  private saveRecentFiles(): void {
    try {
      const Store = require('electron-store');
      const store = new Store();
      store.set('recentFiles', this.recentFiles);
    } catch (error) {
      console.error('Failed to save recent files:', error);
    }
  }

  /**
   * Set up file associations for the app
   */
  public setupFileAssociations(): void {
    // Register file associations for AI Assistant project files
    if (process.platform === 'win32') {
      app.setAsDefaultProtocolClient('ai-assistant');
    }

    // Handle file opening from system
    app.on('open-file', (event, filePath) => {
      event.preventDefault();
      this.handleFileOpen(filePath);
    });

    app.on('open-url', (event, url) => {
      event.preventDefault();
      if (url.startsWith('ai-assistant://')) {
        this.handleProtocolUrl(url);
      }
    });
  }

  /**
   * Handle file opening from system
   */
  private handleFileOpen(filePath: string): void {
    if (this.mainWindow) {
      this.mainWindow.webContents.send('file:system-open', filePath);
      this.addToRecentFiles(filePath);
    }
  }

  /**
   * Handle protocol URL
   */
  private handleProtocolUrl(url: string): void {
    if (this.mainWindow) {
      this.mainWindow.webContents.send('protocol:url-opened', url);
    }
  }

  /**
   * Create file shortcuts/aliases
   */
  public async createShortcut(targetPath: string, shortcutPath: string): Promise<boolean> {
    try {
      if (process.platform === 'win32') {
        // Use shell.writeShortcutLink on Windows
        return shell.writeShortcutLink(shortcutPath, {
          target: targetPath,
          description: 'AI Assistant File Shortcut'
        });
      } else {
        // Create symlink on Unix-like systems
        fs.symlinkSync(targetPath, shortcutPath);
        return true;
      }
    } catch (error) {
      console.error('Failed to create shortcut:', error);
      return false;
    }
  }

  /**
   * Get system directories
   */
  public getSystemDirectories(): { [key: string]: string } {
    const userHome = require('os').homedir();
    
    return {
      home: userHome,
      documents: path.join(userHome, 'Documents'),
      downloads: path.join(userHome, 'Downloads'),
      desktop: path.join(userHome, 'Desktop'),
      pictures: path.join(userHome, 'Pictures'),
      music: path.join(userHome, 'Music'),
      videos: path.join(userHome, 'Videos'),
      temp: require('os').tmpdir()
    };
  }

  /**
   * Clean up resources
   */
  public destroy(): void {
    // Close all file watchers
    for (const [dirPath, watcher] of this.watchedDirectories) {
      watcher.close();
    }
    this.watchedDirectories.clear();

    // Remove all listeners
    this.removeAllListeners();
  }
}

export function createFileSystemIntegration(mainWindow: BrowserWindow): FileSystemIntegration {
  return new FileSystemIntegration(mainWindow);
}