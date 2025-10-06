import React from 'react';
import { ServiceStatusIndicator } from './ServiceStatusIndicator';

interface ComponentStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'offline';
  version?: string;
  error?: string;
}

interface SystemStatus {
  overall_status: 'healthy' | 'degraded' | 'unhealthy' | 'offline';
  llm_status: ComponentStatus;
  stt_status: ComponentStatus;
  tts_status: ComponentStatus;
  automation_status: ComponentStatus;
  learning_status: ComponentStatus;
  security_status: ComponentStatus;
  update_status: ComponentStatus;
  memory_usage?: number;
  cpu_usage?: number;
}

interface StatusBarProps {
  systemStatus: SystemStatus | null;
  isConnected: boolean;
}

const StatusBar: React.FC<StatusBarProps> = ({ systemStatus, isConnected }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'unhealthy':
        return 'bg-red-500';
      case 'offline':
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'Healthy';
      case 'degraded':
        return 'Degraded';
      case 'unhealthy':
        return 'Unhealthy';
      case 'offline':
      default:
        return 'Offline';
    }
  };

  const services = systemStatus ? [
    { name: 'LLM', status: systemStatus.llm_status },
    { name: 'STT', status: systemStatus.stt_status },
    { name: 'TTS', status: systemStatus.tts_status },
    { name: 'Automation', status: systemStatus.automation_status },
    { name: 'Learning', status: systemStatus.learning_status },
    { name: 'Security', status: systemStatus.security_status },
    { name: 'Updates', status: systemStatus.update_status }
  ] : [];

  return (
    <div className="h-8 bg-gray-100 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between px-4 text-xs">
      {/* Connection Status */}
      <div className="flex items-center space-x-2">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-gray-600 dark:text-gray-400">
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {/* Service Status */}
      <ServiceStatusIndicator showDetails={true} />

      {/* Resource Usage */}
      {systemStatus && (systemStatus.memory_usage || systemStatus.cpu_usage) && (
        <div className="flex items-center space-x-3 text-gray-500 dark:text-gray-500">
          {systemStatus.cpu_usage && (
            <span>CPU: {systemStatus.cpu_usage.toFixed(1)}%</span>
          )}
          {systemStatus.memory_usage && (
            <span>RAM: {systemStatus.memory_usage.toFixed(1)}%</span>
          )}
        </div>
      )}

      {/* Version */}
      <div className="text-gray-500 dark:text-gray-500">
        v1.0.0
      </div>
    </div>
  );
};

export default StatusBar;