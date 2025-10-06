/**
 * Icon Manager for handling application icon updates
 */

import { TrayManager } from './tray';
import { NotificationManager } from './notifications';

export type AppStatus = 'idle' | 'listening' | 'processing' | 'error' | 'offline';

export class IconManager {
  private static instance: IconManager;
  private trayManager: TrayManager | null = null;
  private notificationManager: NotificationManager | null = null;
  private currentStatus: AppStatus = 'idle';

  public static getInstance(): IconManager {
    if (!IconManager.instance) {
      IconManager.instance = new IconManager();
    }
    return IconManager.instance;
  }

  private constructor() {
    // Private constructor for singleton
  }

  public setTrayManager(trayManager: TrayManager): void {
    this.trayManager = trayManager;
  }

  public setNotificationManager(notificationManager: NotificationManager): void {
    this.notificationManager = notificationManager;
  }

  public updateStatus(status: AppStatus): void {
    if (this.currentStatus === status) {
      return; // No change needed
    }

    const previousStatus = this.currentStatus;
    this.currentStatus = status;

    // Update tray icon
    if (this.trayManager) {
      this.trayManager.updateTrayIcon(status);
    }

    // Show notifications for status changes if appropriate
    this.handleStatusChangeNotification(previousStatus, status);

    console.log(`App status changed: ${previousStatus} -> ${status}`);
  }

  public getCurrentStatus(): AppStatus {
    return this.currentStatus;
  }

  private handleStatusChangeNotification(previousStatus: AppStatus, newStatus: AppStatus): void {
    if (!this.notificationManager) return;

    // Only show notifications for significant status changes
    switch (newStatus) {
      case 'error':
        if (previousStatus !== 'error') {
          this.notificationManager.showSystemAlert(
            'AI Assistant Error',
            'The AI Assistant has encountered an error. Please check the application.'
          );
        }
        break;
      
      case 'offline':
        if (previousStatus !== 'offline') {
          this.notificationManager.showSystemAlert(
            'AI Assistant Offline',
            'The AI Assistant is currently offline. Attempting to reconnect...'
          );
        }
        break;
      
      case 'idle':
        if (previousStatus === 'offline' || previousStatus === 'error') {
          this.notificationManager.show('status-recovered', {
            title: 'AI Assistant Ready',
            body: 'The AI Assistant is now ready and available.',
            urgency: 'low'
          });
        }
        break;
    }
  }

  public setListening(): void {
    this.updateStatus('listening');
  }

  public setProcessing(): void {
    this.updateStatus('processing');
  }

  public setIdle(): void {
    this.updateStatus('idle');
  }

  public setError(): void {
    this.updateStatus('error');
  }

  public setOffline(): void {
    this.updateStatus('offline');
  }

  // Convenience methods for common status transitions
  public startVoiceInput(): void {
    this.setListening();
  }

  public startProcessing(): void {
    this.setProcessing();
  }

  public finishProcessing(): void {
    this.setIdle();
  }

  public handleError(error?: string): void {
    this.setError();
    
    if (error && this.notificationManager) {
      this.notificationManager.showSystemAlert('AI Assistant Error', error);
    }
  }

  public handleConnectionLost(): void {
    this.setOffline();
  }

  public handleConnectionRestored(): void {
    this.setIdle();
  }
}