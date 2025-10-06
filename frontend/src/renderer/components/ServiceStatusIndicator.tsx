import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { AlertCircle, CheckCircle, Clock, XCircle, RefreshCw } from 'lucide-react';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'offline' | 'unhealthy';
  details?: Record<string, any>;
  error?: string;
  lastCheck?: string;
}

interface ServiceStatusIndicatorProps {
  className?: string;
  showDetails?: boolean;
}

export const ServiceStatusIndicator: React.FC<ServiceStatusIndicatorProps> = ({ 
  className = '', 
  showDetails = false 
}) => {
  const { isConnected, sendMessage } = useWebSocket();
  const [services, setServices] = useState<Record<string, ServiceStatus>>({});
  const [loading, setLoading] = useState(true);
  const [showAllServices, setShowAllServices] = useState(false);

  useEffect(() => {
    fetchServiceStatus();
    
    // Poll for status updates every 30 seconds
    const interval = setInterval(fetchServiceStatus, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchServiceStatus = async () => {
    try {
      const response = await fetch('/api/services/status');
      if (response.ok) {
        const data = await response.json();
        setServices(data.services || {});
      }
    } catch (error) {
      console.error('Failed to fetch service status:', error);
    } finally {
      setLoading(false);
    }
  };

  const restartService = async (serviceName: string) => {
    try {
      const response = await fetch(`/api/services/${serviceName}/restart`, {
        method: 'POST'
      });
      
      if (response.ok) {
        // Refresh status after restart
        setTimeout(fetchServiceStatus, 2000);
      }
    } catch (error) {
      console.error(`Failed to restart service ${serviceName}:`, error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      case 'offline':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'unhealthy':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getOverallStatus = () => {
    const statuses = Object.values(services).map(s => s.status);
    
    if (statuses.includes('offline') || statuses.includes('unhealthy')) {
      return 'error';
    }
    if (statuses.includes('degraded')) {
      return 'warning';
    }
    if (statuses.every(s => s === 'healthy')) {
      return 'healthy';
    }
    return 'unknown';
  };

  const getOverallStatusColor = () => {
    const status = getOverallStatus();
    switch (status) {
      case 'healthy':
        return 'text-green-500';
      case 'warning':
        return 'text-yellow-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  if (loading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <Clock className="w-4 h-4 text-gray-500 animate-spin" />
        <span className="text-sm text-gray-500">Checking services...</span>
      </div>
    );
  }

  const serviceCount = Object.keys(services).length;
  const healthyCount = Object.values(services).filter(s => s.status === 'healthy').length;

  return (
    <div className={`${className}`}>
      {/* Overall Status */}
      <div 
        className="flex items-center space-x-2 cursor-pointer"
        onClick={() => setShowAllServices(!showAllServices)}
      >
        <div className={`w-2 h-2 rounded-full ${
          getOverallStatus() === 'healthy' ? 'bg-green-500' :
          getOverallStatus() === 'warning' ? 'bg-yellow-500' :
          getOverallStatus() === 'error' ? 'bg-red-500' : 'bg-gray-500'
        }`} />
        <span className={`text-sm ${getOverallStatusColor()}`}>
          {isConnected ? `${healthyCount}/${serviceCount} services` : 'Disconnected'}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            fetchServiceStatus();
          }}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          title="Refresh status"
        >
          <RefreshCw className="w-3 h-3 text-gray-500" />
        </button>
      </div>

      {/* Detailed Service List */}
      {showDetails && showAllServices && (
        <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Service Status
          </h4>
          <div className="space-y-2">
            {Object.entries(services).map(([name, service]) => (
              <div key={name} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(service.status)}
                  <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                    {name.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  {service.error && (
                    <span className="text-xs text-red-500 max-w-32 truncate" title={service.error}>
                      {service.error}
                    </span>
                  )}
                  {service.status !== 'healthy' && (
                    <button
                      onClick={() => restartService(name)}
                      className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                      title={`Restart ${name} service`}
                    >
                      Restart
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};