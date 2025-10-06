import React, { useState, useEffect } from 'react';

interface DemoModeProps {
  isOpen: boolean;
  onComplete: () => void;
}

const DemoMode: React.FC<DemoModeProps> = ({ isOpen, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const demoSteps = [
    {
      title: "Welcome to AI Assistant",
      content: "I'm your personal AI assistant, ready to help you automate tasks, control applications, and boost your productivity.",
      action: "greeting"
    },
    {
      title: "Voice & Text Interaction",
      content: "You can communicate with me using voice or text. I understand natural language and can help with complex requests.",
      action: "voice_demo"
    },
    {
      title: "Application Control",
      content: "I can open applications, create documents, browse the web, and automate repetitive tasks across your system.",
      action: "app_demo"
    },
    {
      title: "Self-Healing & Updates",
      content: "I monitor my own health and can fix issues automatically. I also update myself to stay current with new features.",
      action: "healing_demo"
    },
    {
      title: "Learning & Personalization",
      content: "I learn from your usage patterns to provide better suggestions and automate workflows you use frequently.",
      action: "learning_demo"
    }
  ];

  useEffect(() => {
    if (isOpen && currentStep < demoSteps.length) {
      const timer = setTimeout(() => {
        if (currentStep < demoSteps.length - 1) {
          setCurrentStep(prev => prev + 1);
        }
      }, 4000);

      return () => clearTimeout(timer);
    }
  }, [currentStep, isOpen]);

  const handleSkip = () => {
    onComplete();
  };

  const handleNext = () => {
    if (currentStep < demoSteps.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
      onComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const simulateAction = async (action: string) => {
    setIsPlaying(true);
    
    // Simulate different demo actions
    switch (action) {
      case 'greeting':
        // Play greeting sound or animation
        await new Promise(resolve => setTimeout(resolve, 2000));
        break;
      case 'voice_demo':
        // Simulate voice recognition
        await new Promise(resolve => setTimeout(resolve, 3000));
        break;
      case 'app_demo':
        // Simulate opening an application
        await new Promise(resolve => setTimeout(resolve, 2500));
        break;
      case 'healing_demo':
        // Simulate self-healing process
        await new Promise(resolve => setTimeout(resolve, 3500));
        break;
      case 'learning_demo':
        // Simulate learning process
        await new Promise(resolve => setTimeout(resolve, 3000));
        break;
    }
    
    setIsPlaying(false);
  };

  useEffect(() => {
    if (isOpen && currentStep < demoSteps.length) {
      simulateAction(demoSteps[currentStep].action);
    }
  }, [currentStep, isOpen]);

  if (!isOpen) return null;

  const currentDemo = demoSteps[currentStep];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-full max-w-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-500 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                AI Assistant Demo
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Step {currentStep + 1} of {demoSteps.length}
              </p>
            </div>
          </div>
          
          <button
            onClick={handleSkip}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Skip Demo
          </button>
        </div>

        {/* Content */}
        <div className="p-8">
          <div className="text-center mb-8">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              {currentDemo.title}
            </h3>
            <p className="text-lg text-gray-600 dark:text-gray-300 leading-relaxed">
              {currentDemo.content}
            </p>
          </div>

          {/* Demo Animation Area */}
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-8 mb-8 min-h-[200px] flex items-center justify-center">
            {isPlaying ? (
              <div className="text-center">
                <div className="inline-flex items-center space-x-2 text-primary-500">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                  <span className="text-lg font-medium">Demonstrating...</span>
                </div>
              </div>
            ) : (
              <div className="text-center">
                {currentDemo.action === 'greeting' && (
                  <div className="space-y-4">
                    <div className="text-6xl">👋</div>
                    <p className="text-gray-600 dark:text-gray-400">Hello! I'm ready to assist you.</p>
                  </div>
                )}
                
                {currentDemo.action === 'voice_demo' && (
                  <div className="space-y-4">
                    <div className="flex justify-center space-x-2">
                      <div className="voice-wave w-2 h-8 bg-primary-500 rounded"></div>
                      <div className="voice-wave w-2 h-12 bg-primary-500 rounded"></div>
                      <div className="voice-wave w-2 h-6 bg-primary-500 rounded"></div>
                      <div className="voice-wave w-2 h-10 bg-primary-500 rounded"></div>
                      <div className="voice-wave w-2 h-8 bg-primary-500 rounded"></div>
                    </div>
                    <p className="text-gray-600 dark:text-gray-400">"Open Excel and create a new spreadsheet"</p>
                  </div>
                )}
                
                {currentDemo.action === 'app_demo' && (
                  <div className="space-y-4">
                    <div className="text-6xl">📊</div>
                    <p className="text-gray-600 dark:text-gray-400">Opening Excel and creating spreadsheet...</p>
                  </div>
                )}
                
                {currentDemo.action === 'healing_demo' && (
                  <div className="space-y-4">
                    <div className="text-6xl">🔧</div>
                    <p className="text-gray-600 dark:text-gray-400">Self-diagnostic complete. All systems healthy.</p>
                  </div>
                )}
                
                {currentDemo.action === 'learning_demo' && (
                  <div className="space-y-4">
                    <div className="text-6xl">🧠</div>
                    <p className="text-gray-600 dark:text-gray-400">Learning your preferences and usage patterns...</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mb-2">
              <span>Progress</span>
              <span>{Math.round(((currentStep + 1) / demoSteps.length) * 100)}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="bg-primary-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${((currentStep + 1) / demoSteps.length) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>

          <div className="flex space-x-2">
            {demoSteps.map((_, index) => (
              <div
                key={index}
                className={`w-2 h-2 rounded-full ${
                  index === currentStep 
                    ? 'bg-primary-500' 
                    : index < currentStep 
                      ? 'bg-primary-300' 
                      : 'bg-gray-300 dark:bg-gray-600'
                }`}
              />
            ))}
          </div>

          <button
            onClick={handleNext}
            className="px-6 py-2 bg-primary-500 text-white hover:bg-primary-600 rounded-lg transition-colors"
          >
            {currentStep === demoSteps.length - 1 ? 'Get Started' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DemoMode;