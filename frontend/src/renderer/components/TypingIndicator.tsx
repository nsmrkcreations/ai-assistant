import React from 'react';

const TypingIndicator: React.FC = () => {
  return (
    <div className="flex justify-start">
      <div className="max-w-3xl">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-gray-600 dark:text-gray-300">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>

          <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
            <div className="typing-indicator flex items-center space-x-1" data-testid="typing-indicator">
              <span className="w-2 h-2 bg-gray-500 dark:bg-gray-400 rounded-full"></span>
              <span className="w-2 h-2 bg-gray-500 dark:bg-gray-400 rounded-full"></span>
              <span className="w-2 h-2 bg-gray-500 dark:bg-gray-400 rounded-full"></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;