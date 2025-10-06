import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';

interface ChatRequest {
  message: string;
  include_audio?: boolean;
  audio_data?: string;
  context_id?: string | null;
}

interface ChatResponse {
  message: string;
  context_id: string;
  audio_url?: string;
  transcription?: string;
  automation_result?: any;
  suggestions?: Array<{
    id: string;
    text: string;
    action?: string;
    confidence: number;
  }>;
  timestamp: string;
}

interface WebSocketContextType {
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  sendMessage: (request: ChatRequest) => Promise<ChatResponse>;
  lastMessage: any;
  reconnect: () => void;
  queueSize: number;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: React.ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageCallbacksRef = useRef<Map<string, (response: ChatResponse) => void>>(new Map());
  const messageQueueRef = useRef<Array<{ request: ChatRequest; resolve: (value: ChatResponse) => void; reject: (error: any) => void; timestamp: number }>>([]);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 10;

  const startHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearInterval(heartbeatTimeoutRef.current);
    }

    heartbeatTimeoutRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, 30000); // 30 second heartbeat
  }, []);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearInterval(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  const processMessageQueue = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const queuedMessages = [...messageQueueRef.current];
    messageQueueRef.current = [];

    queuedMessages.forEach(({ request, resolve, reject, timestamp }) => {
      // Check if message is too old (5 minutes)
      if (Date.now() - timestamp > 300000) {
        reject(new Error('Message expired'));
        return;
      }

      // Resend the message
      sendMessageInternal(request).then(resolve).catch(reject);
    });
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      return; // Already connecting
    }

    setConnectionState('connecting');

    try {
      const ws = new WebSocket('ws://localhost:8000/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionState('connected');
        reconnectAttempts.current = 0;

        // Clear reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }

        // Process queued messages
        processMessageQueue();

        // Start heartbeat
        startHeartbeat();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle pong responses
          if (data.type === 'pong') {
            return;
          }

          setLastMessage(data);

          // Handle chat responses
          if (data.type === 'chat_response') {
            const messageId = data.data.context_id;
            const callback = messageCallbacksRef.current.get(messageId);
            if (callback) {
              callback(data.data);
              messageCallbacksRef.current.delete(messageId);
            }
          }

          // Handle settings updates
          if (data.type === 'settings_updated') {
            // Notify components about settings changes
            window.dispatchEvent(new CustomEvent('settings-updated', { detail: data.data }));
          }

          // Handle service status updates
          if (data.type === 'service_status') {
            // Update icon manager based on service status
            if (window.electronAPI?.updateServiceStatus) {
              window.electronAPI.updateServiceStatus(data.data);
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionState('disconnected');
        wsRef.current = null;
        stopHeartbeat();

        // Clear pending callbacks with error
        messageCallbacksRef.current.forEach(callback => {
          callback({
            message: 'Connection lost',
            context_id: '',
            timestamp: new Date().toISOString()
          } as ChatResponse);
        });
        messageCallbacksRef.current.clear();

        // Attempt to reconnect if not intentionally closed
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const timeout = Math.min(Math.pow(2, reconnectAttempts.current) * 1000, 30000);
          console.log(`Reconnecting in ${timeout}ms (attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, timeout);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setConnectionState('error');
          console.error('Max reconnection attempts reached');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionState('error');
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionState('error');

      // Retry connection
      if (reconnectAttempts.current < maxReconnectAttempts) {
        const timeout = Math.min(Math.pow(2, reconnectAttempts.current) * 1000, 30000);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, timeout);
      }
    }
  }, [processMessageQueue, startHeartbeat, stopHeartbeat]);

  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttempts.current = 0;
    if (wsRef.current) {
      wsRef.current.close();
    }
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      stopHeartbeat();
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [connect, stopHeartbeat]);

  const sendMessageInternal = async (request: ChatRequest): Promise<ChatResponse> => {
    return new Promise((resolve, reject) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      try {
        const messageId = Date.now().toString();

        // Store callback for response
        messageCallbacksRef.current.set(messageId, resolve);

        // Set timeout for response
        setTimeout(() => {
          if (messageCallbacksRef.current.has(messageId)) {
            messageCallbacksRef.current.delete(messageId);
            reject(new Error('Message timeout'));
          }
        }, 30000); // 30 second timeout

        // Send message
        wsRef.current.send(JSON.stringify({
          type: 'chat',
          data: {
            ...request,
            context_id: messageId
          }
        }));

      } catch (error) {
        reject(error);
      }
    });
  };

  const sendMessage = async (request: ChatRequest): Promise<ChatResponse> => {
    // If WebSocket is connected, send directly
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        return await sendMessageInternal(request);
      } catch (error) {
        console.warn('WebSocket send failed, falling back to HTTP:', error);
      }
    }

    // If WebSocket is connecting, queue the message
    if (connectionState === 'connecting') {
      return new Promise((resolve, reject) => {
        messageQueueRef.current.push({
          request,
          resolve,
          reject,
          timestamp: Date.now()
        });
      });
    }

    // If WebSocket is disconnected or error, try to reconnect and queue message
    if (connectionState === 'disconnected' || connectionState === 'error') {
      reconnect();
      return new Promise((resolve, reject) => {
        messageQueueRef.current.push({
          request,
          resolve,
          reject,
          timestamp: Date.now()
        });
      });
    }

    // Fallback to HTTP API
    try {
      return await sendHttpMessage(request);
    } catch (error) {
      console.error('Both WebSocket and HTTP failed:', error);
      throw error;
    }
  };

  const sendHttpMessage = async (request: ChatRequest): Promise<ChatResponse> => {
    try {
      const response = await fetch('http://localhost:8000/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('HTTP request failed:', error);
      throw error;
    }
  };

  const value: WebSocketContextType = {
    isConnected,
    connectionState,
    sendMessage,
    lastMessage,
    reconnect,
    queueSize: messageQueueRef.current.length
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};