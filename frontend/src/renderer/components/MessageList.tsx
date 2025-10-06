import React from 'react';
import MessageBubble from './MessageBubble';

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

interface MessageListProps {
  messages: Message[];
  onSuggestionClick: (suggestion: any) => void;
}

const MessageList: React.FC<MessageListProps> = ({ messages, onSuggestionClick }) => {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onSuggestionClick={onSuggestionClick}
        />
      ))}
    </div>
  );
};

export default MessageList;