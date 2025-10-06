/**
 * Background Monitor for AI Assistant
 * Handles proactive assistance and system monitoring
 */

import { BrowserWindow, ipcMain, powerMonitor, screen } from 'electron';
import { EventEmitter } from 'events';
import * as os from 'os';
import * as fs from 'fs';
import * as path from 'path';

interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkActivity: boolean;
  activeWindow?: string;
  idleTime: number;
}

interface UserActivity {
  type: 'keyboard' | 'mouse' | 'window_change' | 'app_launch' | 'file_access';
  timestamp: number;
  details: any;
}

export class BackgroundMonitor extends EventEmitter {
  private mainWindow: BrowserWindow | null = null;
  private isMonitoring = false;
  private monitoringInterval: NodeJS.Timeout | null = null;
  private activityLog: UserActivity[] = [];
  private lastSystemMetrics: SystemMetrics | null = null;
  private proactiveAssistanceEnabled = true;
  
  // Monitoring intervals (in milliseconds)
  private readonly SYSTEM_MONITOR_INTERVAL = 5000; // 5 seconds
  private readonly ACTIVITY_LOG_MAX_SIZE = 1000;
  private readonly IDLE_THRESHOLD = 300000; // 5 minutes

  constructor(mainWindow: BrowserWindow) {
    super();
    this.mainWindow = mainWindow;
    this.setupEventListeners();
  }

  /**
   * Start background monitoring
   */
  startMonitoring(): void {
    if (this.isMonitoring) return;

    this.isMonitoring = true;
    console.log('Background monitoring started');

    // Start system metrics monitoring
    this.monitoringInterval = setInterval(() => {
      this.collectSystemMetrics();
    }, this.SYSTEM_MONITOR_INTERVAL);

    // Start power monitoring
    this.setupPowerMonitoring();

    // Start screen monitoring
    this.setupScreenMonitoring();

    this.emit('monitoring-started');
  }

  /**
   * Stop background monitoring
   */
  stopMonitoring(): void {
    if (!this.isMonitoring) return;

    this.isMonitoring = false;
    console.log('Background monitoring stopped');

    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }

    this.emit('monitoring-stopped');
  }

  /**
   * Set up event listeners for system events
   */
  private setupEventListeners(): void {
    // IPC listeners for renderer process
    ipcMain.handle('background-monitor:get-status', () => {
      return {
        isMonitoring: this.isMonitoring,
        lastMetrics: this.lastSystemMetrics,
        activityCount: this.activityLog.length,
        proactiveAssistanceEnabled: this.proactiveAssistanceEnabled
      };
    });

    ipcMain.handle('background-monitor:toggle-proactive-assistance', (_, enabled: boolean) => {
      this.proactiveAssistanceEnabled = enabled;
      return this.proactiveAssistanceEnabled;
    });

    ipcMain.handle('background-monitor:get-activity-log', () => {
      return this.activityLog.slice(-50); // Return last 50 activities
    });

    // Window events
    if (this.mainWindow) {
      this.mainWindow.on('focus', () => {
        this.logActivity('window_change', { action: 'focus', window: 'ai-assistant' });
      });

      this.mainWindow.on('blur', () => {
        this.logActivity('window_change', { action: 'blur', window: 'ai-assistant' });
      });
    }
  }

  /**
   * Set up power monitoring
   */
  private setupPowerMonitoring(): void {
    powerMonitor.on('suspend', () => {
      console.log('System is going to sleep');
      this.logActivity('system', { action: 'suspend' });
      this.emit('system-suspend');
    });

    powerMonitor.on('resume', () => {
      console.log('System has resumed from sleep');
      this.logActivity('system', { action: 'resume' });
      this.emit('system-resume');
      
      // Check for proactive assistance opportunities after resume
      this.checkProactiveOpportunities();
    });

    powerMonitor.on('on-ac', () => {
      this.logActivity('system', { action: 'power-connected' });
    });

    powerMonitor.on('on-battery', () => {
      this.logActivity('system', { action: 'power-disconnected' });
      this.emit('power-status-changed', 'battery');
    });

    powerMonitor.on('shutdown', () => {
      console.log('System is shutting down');
      this.logActivity('system', { action: 'shutdown' });
      this.stopMonitoring();
    });

    powerMonitor.on('lock-screen', () => {
      this.logActivity('system', { action: 'screen-locked' });
    });

    powerMonitor.on('unlock-screen', () => {
      this.logActivity('system', { action: 'screen-unlocked' });
      this.checkProactiveOpportunities();
    });
  }

  /**
   * Set up screen monitoring
   */
  private setupScreenMonitoring(): void {
    // Monitor display changes
    screen.on('display-added', (event, newDisplay) => {
      this.logActivity('system', { 
        action: 'display-added', 
        display: { id: newDisplay.id, bounds: newDisplay.bounds }
      });
    });

    screen.on('display-removed', (event, oldDisplay) => {
      this.logActivity('system', { 
        action: 'display-removed', 
        display: { id: oldDisplay.id }
      });
    });

    screen.on('display-metrics-changed', (event, display, changedMetrics) => {
      this.logActivity('system', { 
        action: 'display-changed', 
        display: { id: display.id },
        changes: changedMetrics
      });
    });
  }

  /**
   * Collect system metrics
   */
  private async collectSystemMetrics(): Promise<void> {
    try {
      const metrics: SystemMetrics = {
        cpuUsage: await this.getCpuUsage(),
        memoryUsage: this.getMemoryUsage(),
        diskUsage: await this.getDiskUsage(),
        networkActivity: await this.getNetworkActivity(),
        idleTime: powerMonitor.getSystemIdleTime() * 1000 // Convert to milliseconds
      };

      this.lastSystemMetrics = metrics;
      
      // Emit metrics for interested listeners
      this.emit('system-metrics', metrics);

      // Check for performance issues
      this.checkPerformanceIssues(metrics);

      // Check for proactive assistance opportunities
      if (this.proactiveAssistanceEnabled) {
        this.checkProactiveOpportunities();
      }

    } catch (error) {
      console.error('Error collecting system metrics:', error);
    }
  }

  /**
   * Get CPU usage percentage
   */
  private async getCpuUsage(): Promise<number> {
    return new Promise((resolve) => {
      const startMeasure = process.cpuUsage();
      
      setTimeout(() => {
        const endMeasure = process.cpuUsage(startMeasure);
        const totalUsage = endMeasure.user + endMeasure.system;
        const percentage = (totalUsage / 1000000) * 100; // Convert to percentage
        resolve(Math.min(percentage, 100));
      }, 100);
    });
  }

  /**
   * Get memory usage percentage
   */
  private getMemoryUsage(): number {
    const totalMemory = os.totalmem();
    const freeMemory = os.freemem();
    const usedMemory = totalMemory - freeMemory;
    return (usedMemory / totalMemory) * 100;
  }

  /**
   * Get disk usage percentage
   */
  private async getDiskUsage(): Promise<number> {
    try {
      // This is a simplified implementation
      // In a real app, you might want to use a library like 'node-disk-info'
      const stats = fs.statSync(os.homedir());
      return 50; // Placeholder - implement actual disk usage calculation
    } catch (error) {
      return 0;
    }
  }

  /**
   * Check network activity
   */
  private async getNetworkActivity(): Promise<boolean> {
    // Simplified network activity check
    // In a real implementation, you might monitor network interfaces
    return Math.random() > 0.5; // Placeholder
  }

  /**
   * Log user activity
   */
  private logActivity(type: UserActivity['type'], details: any): void {
    const activity: UserActivity = {
      type,
      timestamp: Date.now(),
      details
    };

    this.activityLog.push(activity);

    // Keep log size manageable
    if (this.activityLog.length > this.ACTIVITY_LOG_MAX_SIZE) {
      this.activityLog = this.activityLog.slice(-this.ACTIVITY_LOG_MAX_SIZE / 2);
    }

    this.emit('user-activity', activity);
  }

  /**
   * Check for performance issues and suggest optimizations
   */
  private checkPerformanceIssues(metrics: SystemMetrics): void {
    const issues: string[] = [];

    if (metrics.cpuUsage > 80) {
      issues.push('High CPU usage detected');
    }

    if (metrics.memoryUsage > 85) {
      issues.push('High memory usage detected');
    }

    if (metrics.diskUsage > 90) {
      issues.push('Low disk space detected');
    }

    if (issues.length > 0) {
      this.emit('performance-issues', issues);
      
      if (this.proactiveAssistanceEnabled) {
        this.suggestPerformanceOptimizations(issues);
      }
    }
  }

  /**
   * Check for proactive assistance opportunities
   */
  private checkProactiveOpportunities(): void {
    if (!this.proactiveAssistanceEnabled || !this.lastSystemMetrics) return;

    const now = Date.now();
    const recentActivities = this.activityLog.filter(
      activity => now - activity.timestamp < 300000 // Last 5 minutes
    );

    // Check for patterns that might benefit from assistance
    const patterns = this.analyzeActivityPatterns(recentActivities);
    
    if (patterns.length > 0) {
      this.emit('proactive-opportunities', patterns);
    }

    // Check for idle time
    if (this.lastSystemMetrics.idleTime > this.IDLE_THRESHOLD) {
      this.emit('user-idle', this.lastSystemMetrics.idleTime);
    }
  }

  /**
   * Analyze activity patterns for proactive assistance
   */
  private analyzeActivityPatterns(activities: UserActivity[]): string[] {
    const patterns: string[] = [];

    // Example patterns - extend based on your needs
    const windowChanges = activities.filter(a => a.type === 'window_change').length;
    if (windowChanges > 10) {
      patterns.push('frequent-window-switching');
    }

    const fileAccesses = activities.filter(a => a.type === 'file_access').length;
    if (fileAccesses > 5) {
      patterns.push('heavy-file-activity');
    }

    return patterns;
  }

  /**
   * Suggest performance optimizations
   */
  private suggestPerformanceOptimizations(issues: string[]): void {
    const suggestions: string[] = [];

    issues.forEach(issue => {
      switch (issue) {
        case 'High CPU usage detected':
          suggestions.push('Consider closing unnecessary applications or restarting your computer');
          break;
        case 'High memory usage detected':
          suggestions.push('Close unused browser tabs and applications to free up memory');
          break;
        case 'Low disk space detected':
          suggestions.push('Clean up temporary files or move files to external storage');
          break;
      }
    });

    if (suggestions.length > 0 && this.mainWindow) {
      this.mainWindow.webContents.send('performance-suggestions', suggestions);
    }
  }

  /**
   * Get monitoring statistics
   */
  getStats(): any {
    return {
      isMonitoring: this.isMonitoring,
      activityLogSize: this.activityLog.length,
      lastMetrics: this.lastSystemMetrics,
      proactiveAssistanceEnabled: this.proactiveAssistanceEnabled,
      uptime: process.uptime()
    };
  }

  /**
   * Enable/disable proactive assistance
   */
  setProactiveAssistance(enabled: boolean): void {
    this.proactiveAssistanceEnabled = enabled;
    console.log(`Proactive assistance ${enabled ? 'enabled' : 'disabled'}`);
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this.stopMonitoring();
    this.removeAllListeners();
    this.activityLog = [];
  }
}

export function createBackgroundMonitor(mainWindow: BrowserWindow): BackgroundMonitor {
  return new BackgroundMonitor(mainWindow);
}