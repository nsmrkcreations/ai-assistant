/**
 * Desktop Notifications Manager
 */

import { Notification, nativeImage, NotificationConstructorOptions } from 'electron';
import { EventEmitter } from 'events';
import * as path from 'path';

export interface NotificationOptions {
  title: string;
  body: string;
  icon?: string;
  silent?: boolean;
  urgency?: 'normal' | 'critical' | 'low';
  actions?: Array<{
    type: 'button';
    text: string;
  }>;
}

export function setupNotifications(): NotificationManager {
  return NotificationManager.getInstance();
}

export class NotificationManager extends EventEmitter {
  private static instance: NotificationManager;
  private notifications: Map<string, Notification> = new Map();

  public static getInstance(): NotificationManager {
    if (!NotificationManager.instance) {
      NotificationManager.instance = new NotificationManager();
    }
    return NotificationManager.instance;
  }

  private constructor() {
    super();
    // Private constructor for singleton
  }

  public async show(id: string, options: NotificationOptions): Promise<void> {
    // Check if notifications are supported
    if (!Notification.isSupported()) {
      console.warn('Notifications are not supported on this system');
      return;
    }

    // Close existing notification with same ID
    this.close(id);

    // Create notification
    const notification = new Notification({
      title: options.title,
      body: options.body,
      icon: options.icon ? nativeImage.createFromPath(options.icon) : this.getDefaultIcon(),
      silent: options.silent || false,
      urgency: options.urgency || 'normal',
      actions: options.actions || []
    });

    // Store notification
    this.notifications.set(id, notification);

    // Handle notification events
    notification.on('click', () => {
      this.handleNotificationClick(id, options);
    });

    notification.on('close', () => {
      this.notifications.delete(id);
    });

    notification.on('action', (_, index) => {
      this.handleNotificationAction(id, index, options);
    });

    // Show notification
    notification.show();
  }

  public close(id: string): void {
    const notification = this.notifications.get(id);
    if (notification) {
      notification.close();
      this.notifications.delete(id);
    }
  }

  public closeAll(): void {
    for (const [id, notification] of this.notifications) {
      notification.close();
    }
    this.notifications.clear();
  }

  private getDefaultIcon(): Electron.NativeImage {
    const isDev = process.env.NODE_ENV === 'development';
    const basePath = isDev ? process.cwd() : process.resourcesPath;
    const iconPath = path.join(basePath, 'assets', 'icon.png');
    
    return nativeImage.createFromPath(iconPath);
  }

  private handleNotificationClick(notificationId: string, options: NotificationOptions): void {
    console.log(`Notification clicked: ${notificationId}`);
    
    // Emit custom event for notification click
    this.emit('notification-click', notificationId, options);
  }

  private handleNotificationAction(notificationId: string, actionIndex: number, options: NotificationOptions): void {
    const action = options.actions?.[actionIndex];
    if (action) {
      console.log(`Notification action: ${notificationId}, ${action.type}`);
      
      // Emit custom event for notification action
      this.emit('notification-action', notificationId, action.type, options);
    }
  }

  // Predefined notification types
  public showTaskComplete(taskName: string): void {
    this.show('task-complete', {
      title: 'Task Completed',
      body: `Successfully completed: ${taskName}`,
      urgency: 'normal'
    });
  }

  public showTaskFailed(taskName: string, error: string): void {
    this.show('task-failed', {
      title: 'Task Failed',
      body: `Failed to complete: ${taskName}\nError: ${error}`,
      urgency: 'critical'
    });
  }

  public showVoiceCommandReady(): void {
    this.show('voice-ready', {
      title: 'Voice Command Ready',
      body: 'Listening for your command...',
      silent: true,
      urgency: 'low'
    });
  }

  public showNewMessage(message: string): void {
    this.show('new-message', {
      title: 'AI Assistant',
      body: message,
      actions: [
        { type: 'button', text: 'Reply' },
        { type: 'button', text: 'Dismiss' }
      ]
    });
  }

  public showSystemAlert(title: string, message: string): void {
    this.show('system-alert', {
      title,
      body: message,
      urgency: 'critical'
    });
  }

  public showUpdateAvailable(version: string): void {
    this.show('update-available', {
      title: 'Update Available',
      body: `AI Assistant ${version} is available for download`,
      actions: [
        { type: 'button', text: 'Update Now' },
        { type: 'button', text: 'Later' }
      ]
    });
  }

  public showLearningInsight(insight: string): void {
    this.show('learning-insight', {
      title: 'Learning Insight',
      body: insight,
      urgency: 'low',
      actions: [
        { type: 'button', text: 'Apply Suggestion' },
        { type: 'button', text: 'Ignore' }
      ]
    });
  }

  // Event listener convenience methods
  public onNotificationClick(callback: (notificationId: string, options: NotificationOptions) => void): void {
    this.on('notification-click', callback);
  }

  public onNotificationAction(callback: (notificationId: string, actionType: string, options: NotificationOptions) => void): void {
    this.on('notification-action', callback);
  }

  public removeNotificationListeners(): void {
    this.removeAllListeners('notification-click');
    this.removeAllListeners('notification-action');
  }
}