import React, { useState, useRef, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import VoiceInput from './VoiceInput';
import MessageList from './MessageList';
import TextInput from './TextInput';
import TypingIndicator from './TypingIndicator';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  audioUrl?: string;
  transcription?: string;
  suggestions?: Array<{
    id: string;
    text: string;
    action?: string;
    confidence: number;
  }>;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { sendMessage, isConnected } = useWebSocket();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (content: string, isVoice: boolean = false) => {
    if (!content.trim() || !isConnected) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: content.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      // Send to backend
      const response = await sendMessage({
        message: content.trim(),
        include_audio: true,
        context_id: null
      });

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.message,
        timestamp: new Date(),
        audioUrl: response.audio_url,
        transcription: response.transcription,
        suggestions: response.suggestions
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Play audio if available
      if (response.audio_url) {
        const audio = new Audio(`http://localhost:8000${response.audio_url}`);
        audio.play().catch(console.error);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleVoiceInput = async (audioBlob: Blob) => {
    if (!isConnected) return;

    setIsTyping(true);

    try {
      // Create form data
      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice.wav');

      // Send to backend
      const response = await fetch('http://localhost:8000/chat/voice', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Voice processing failed');
      }

      const result = await response.json();

      // Add user message with transcription
      const userMessage: Message = {
        id: Date.now().toString(),
        type: 'user',
        content: result.transcription || 'Voice input',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, userMessage]);

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: result.message,
        timestamp: new Date(),
        audioUrl: result.audio_url,
        suggestions: result.suggestions
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Play audio if available
      if (result.audio_url) {
        const audio = new Audio(`http://localhost:8000${result.audio_url}`);
        audio.play().catch(console.error);
      }

    } catch (error) {
      console.error('Error processing voice input:', error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sorry, I couldn\'t process your voice input. Please try again.',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSuggestionClick = (suggestion: any) => {
    handleSendMessage(suggestion.text);
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">AI Assistant</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={clearChat}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            title="Clear chat"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Welcome to AI Assistant
            </h3>
            <p className="text-gray-500 dark:text-gray-400 max-w-md">
              I'm here to help you with tasks, automation, and productivity. 
              You can type a message or use voice input to get started.
            </p>
          </div>
        ) : (
          <>
            <MessageList 
              messages={messages} 
              onSuggestionClick={handleSuggestionClick}
            />
            {isTyping && <TypingIndicator />}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-end space-x-3">
          <div className="flex-1">
            <TextInput
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSendMessage}
              disabled={!isConnected || isTyping}
              placeholder={isConnected ? "Type your message..." : "Connecting..."}
            />
          </div>
          <VoiceInput
            onVoiceInput={handleVoiceInput}
            disabled={!isConnected || isTyping}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;