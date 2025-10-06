import { useState, useEffect } from 'react';

interface ComponentStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'offline';
  version?: string;
  last_check: string;
  details: Record<string, any>;
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
  timestamp: string;
  uptime?: number;
  memory_usage?: number;
  cpu_usage?: number;
}

export const useSystemStatus = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/system/status');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const status = await response.json();
      setSystemStatus(status);
      setIsConnected(true);
      setError(null);
    } catch (err) {
      console.error('Error fetching system status:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsConnected(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchSystemStatus();

    // Set up polling every 30 seconds
    const interval = setInterval(fetchSystemStatus, 30000);

    return () => clearInterval(interval);
  }, []);

  return {
    systemStatus,
    isConnected,
    error,
    refetch: fetchSystemStatus
  };
};