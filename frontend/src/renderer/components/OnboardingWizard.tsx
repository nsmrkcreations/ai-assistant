import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronLeft, Check, Mic, Settings, Zap, Shield } from 'lucide-react';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  component: React.ComponentType<any>;
  optional?: boolean;
}

interface OnboardingWizardProps {
  onComplete: (settings: any) => void;
  onSkip: () => void;
}

const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete, onSkip }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [settings, setSettings] = useState({
    voiceEnabled: false,
    voiceCalibrated: false,
    autoStart: true,
    minimizeToTray: true,
    theme: 'system',
    privacySettings: {
      dataCollection: true,
      analytics: false,
      conversationLogging: true
    },
    preferences: {
      preferredFileTypes: [],
      workingHours: { start: 9, end: 17 },
      notifications: true
    }
  });

  const steps: OnboardingStep[] = [
    {
      id: 'welcome',
      title: 'Welcome to AI Assistant',
      description: 'Your personal AI employee is ready to help you be more productive',
      component: WelcomeStep
    },
    {
      id: 'voice_setup',
      title: 'Voice Setup',
      description: 'Configure voice recognition for hands-free interaction',
      component: VoiceSetupStep
    },
    {
      id: 'preferences',
      title: 'Preferences',
      description: 'Customize your AI Assistant experience',
      component: PreferencesStep
    },
    {
      id: 'privacy',
      title: 'Privacy Settings',
      description: 'Control your data and privacy preferences',
      component: PrivacyStep
    },
    {
      id: 'features',
      title: 'Key Features',
      description: 'Learn about what your AI Assistant can do',
      component: FeaturesStep
    },
    {
      id: 'complete',
      title: 'Setup Complete',
      description: 'You\'re all set! Let\'s start being productive',
      component: CompleteStep
    }
  ];

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete(settings);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const updateSettings = (newSettings: any) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  };

  const CurrentStepComponent = steps[currentStep].component;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden">
        {/* Progress Bar */}
        <div className="bg-gray-100 dark:bg-gray-700 px-6 py-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Setup Wizard
            </h2>
            <button
              onClick={onSkip}
              className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              Skip Setup
            </button>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
            <span>Step {currentStep + 1} of {steps.length}</span>
            <span>{Math.round(((currentStep + 1) / steps.length) * 100)}% Complete</span>
          </div>
        </div>

        {/* Step Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          <div className="text-center mb-6">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              {steps[currentStep].title}
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              {steps[currentStep].description}
            </p>
          </div>

          <CurrentStepComponent
            settings={settings}
            updateSettings={updateSettings}
            onNext={nextStep}
          />
        </div>

        {/* Navigation */}
        <div className="bg-gray-50 dark:bg-gray-700 px-6 py-4 flex justify-between">
          <button
            onClick={prevStep}
            disabled={currentStep === 0}
            className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-md hover:bg-gray-50 dark:hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Previous
          </button>

          <button
            onClick={nextStep}
            className="flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {currentStep === steps.length - 1 ? 'Complete Setup' : 'Next'}
            <ChevronRight className="w-4 h-4 ml-1" />
          </button>
        </div>
      </div>
    </div>
  );
};

// Welcome Step Component
const WelcomeStep: React.FC<any> = () => {
  return (
    <div className="text-center">
      <div className="w-24 h-24 mx-auto mb-6 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
        <Zap className="w-12 h-12 text-blue-600 dark:text-blue-400" />
      </div>
      
      <div className="space-y-4 text-left max-w-md mx-auto">
        <div className="flex items-start space-x-3">
          <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white">Voice-Activated Assistant</h4>
            <p className="text-sm text-gray-600 dark:text-gray-300">Talk to your AI naturally with advanced speech recognition</p>
          </div>
        </div>
        
        <div className="flex items-start space-x-3">
          <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white">Intelligent Automation</h4>
            <p className="text-sm text-gray-600 dark:text-gray-300">Automate repetitive tasks and workflows</p>
          </div>
        </div>
        
        <div className="flex items-start space-x-3">
          <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white">Creative Generation</h4>
            <p className="text-sm text-gray-600 dark:text-gray-300">Generate images, documents, and multimedia content</p>
          </div>
        </div>
        
        <div className="flex items-start space-x-3">
          <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white">Always Learning</h4>
            <p className="text-sm text-gray-600 dark:text-gray-300">Adapts to your preferences and work patterns</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Voice Setup Step Component
const VoiceSetupStep: React.FC<any> = ({ settings, updateSettings }) => {
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [calibrationStep, setCalibrationStep] = useState(0);
  const [microphoneAccess, setMicrophoneAccess] = useState<boolean | null>(null);

  const calibrationSteps = [
    "Please say: 'Hello AI Assistant'",
    "Now say: 'Create a new document'",
    "Finally say: 'What's the weather today?'"
  ];

  useEffect(() => {
    // Check microphone access
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(() => {
        setMicrophoneAccess(true);
      })
      .catch(() => {
        setMicrophoneAccess(false);
      });
  }, []);

  const startCalibration = async () => {
    setIsCalibrating(true);
    setCalibrationStep(0);
    
    // Simulate calibration process
    for (let i = 0; i < calibrationSteps.length; i++) {
      setCalibrationStep(i);
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
    
    setIsCalibrating(false);
    updateSettings({ voiceEnabled: true, voiceCalibrated: true });
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-20 h-20 mx-auto mb-4 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
          <Mic className="w-10 h-10 text-blue-600 dark:text-blue-400" />
        </div>
      </div>

      {microphoneAccess === false && (
        <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded-md p-4">
          <p className="text-red-800 dark:text-red-200 text-sm">
            Microphone access is required for voice features. Please allow microphone access in your browser settings.
          </p>
        </div>
      )}

      {microphoneAccess === true && (
        <div className="space-y-4">
          <div className="bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700 rounded-md p-4">
            <p className="text-green-800 dark:text-green-200 text-sm">
              ✓ Microphone access granted
            </p>
          </div>

          {!settings.voiceCalibrated && !isCalibrating && (
            <div className="text-center">
              <button
                onClick={startCalibration}
                className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Start Voice Calibration
              </button>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
                This helps improve voice recognition accuracy
              </p>
            </div>
          )}

          {isCalibrating && (
            <div className="text-center space-y-4">
              <div className="animate-pulse">
                <div className="w-16 h-16 mx-auto bg-red-500 rounded-full flex items-center justify-center">
                  <Mic className="w-8 h-8 text-white" />
                </div>
              </div>
              <p className="text-lg font-medium text-gray-900 dark:text-white">
                {calibrationSteps[calibrationStep]}
              </p>
              <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${((calibrationStep + 1) / calibrationSteps.length) * 100}%` }}
                />
              </div>
            </div>
          )}

          {settings.voiceCalibrated && (
            <div className="text-center">
              <div className="w-16 h-16 mx-auto bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mb-4">
                <Check className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <p className="text-lg font-medium text-green-600 dark:text-green-400">
                Voice calibration complete!
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
                You can now use voice commands with your AI Assistant
              </p>
            </div>
          )}
        </div>
      )}

      <div className="space-y-3">
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={settings.voiceEnabled}
            onChange={(e) => updateSettings({ voiceEnabled: e.target.checked })}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
            Enable voice commands
          </span>
        </label>
      </div>
    </div>
  );
};

// Preferences Step Component
const PreferencesStep: React.FC<any> = ({ settings, updateSettings }) => {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-20 h-20 mx-auto mb-4 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center">
          <Settings className="w-10 h-10 text-purple-600 dark:text-purple-400" />
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Theme Preference
          </label>
          <select
            value={settings.theme}
            onChange={(e) => updateSettings({ theme: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          >
            <option value="system">Follow System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Working Hours
          </label>
          <div className="flex space-x-4">
            <div className="flex-1">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Start</label>
              <select
                value={settings.preferences.workingHours.start}
                onChange={(e) => updateSettings({
                  preferences: {
                    ...settings.preferences,
                    workingHours: {
                      ...settings.preferences.workingHours,
                      start: parseInt(e.target.value)
                    }
                  }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>{i.toString().padStart(2, '0')}:00</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">End</label>
              <select
                value={settings.preferences.workingHours.end}
                onChange={(e) => updateSettings({
                  preferences: {
                    ...settings.preferences,
                    workingHours: {
                      ...settings.preferences.workingHours,
                      end: parseInt(e.target.value)
                    }
                  }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>{i.toString().padStart(2, '0')}:00</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={settings.autoStart}
              onChange={(e) => updateSettings({ autoStart: e.target.checked })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Start AI Assistant when computer starts
            </span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={settings.minimizeToTray}
              onChange={(e) => updateSettings({ minimizeToTray: e.target.checked })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Minimize to system tray when closed
            </span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={settings.preferences.notifications}
              onChange={(e) => updateSettings({
                preferences: {
                  ...settings.preferences,
                  notifications: e.target.checked
                }
              })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Enable desktop notifications
            </span>
          </label>
        </div>
      </div>
    </div>
  );
};

// Privacy Step Component
const PrivacyStep: React.FC<any> = ({ settings, updateSettings }) => {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-20 h-20 mx-auto mb-4 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
          <Shield className="w-10 h-10 text-green-600 dark:text-green-400" />
        </div>
      </div>

      <div className="bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700 rounded-md p-4">
        <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">Your Privacy Matters</h4>
        <p className="text-sm text-blue-800 dark:text-blue-200">
          All data is stored locally on your device. You have full control over what information is collected and how it's used.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="flex items-start">
            <input
              type="checkbox"
              checked={settings.privacySettings.dataCollection}
              onChange={(e) => updateSettings({
                privacySettings: {
                  ...settings.privacySettings,
                  dataCollection: e.target.checked
                }
              })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Enable data collection for personalization
              </span>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Allows the AI to learn your preferences and provide better assistance
              </p>
            </div>
          </label>
        </div>

        <div>
          <label className="flex items-start">
            <input
              type="checkbox"
              checked={settings.privacySettings.conversationLogging}
              onChange={(e) => updateSettings({
                privacySettings: {
                  ...settings.privacySettings,
                  conversationLogging: e.target.checked
                }
              })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Save conversation history
              </span>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Keeps a record of your conversations for context and continuity
              </p>
            </div>
          </label>
        </div>

        <div>
          <label className="flex items-start">
            <input
              type="checkbox"
              checked={settings.privacySettings.analytics}
              onChange={(e) => updateSettings({
                privacySettings: {
                  ...settings.privacySettings,
                  analytics: e.target.checked
                }
              })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Anonymous usage analytics
              </span>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Helps improve the AI Assistant with anonymous usage data
              </p>
            </div>
          </label>
        </div>
      </div>

      <div className="bg-gray-50 dark:bg-gray-700 rounded-md p-4">
        <h5 className="font-medium text-gray-900 dark:text-white mb-2">Data Rights</h5>
        <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1">
          <li>• Export your data at any time</li>
          <li>• Delete all personal data</li>
          <li>• Modify privacy settings anytime</li>
          <li>• Full transparency on data usage</li>
        </ul>
      </div>
    </div>
  );
};

// Features Step Component
const FeaturesStep: React.FC<any> = () => {
  const features = [
    {
      icon: "🎤",
      title: "Voice Commands",
      description: "Talk naturally to your AI assistant",
      example: "Try: 'Create a presentation about AI trends'"
    },
    {
      icon: "🤖",
      title: "Intelligent Automation",
      description: "Automate repetitive tasks and workflows",
      example: "Try: 'Organize my desktop files by type'"
    },
    {
      icon: "🎨",
      title: "Creative Generation",
      description: "Generate images, documents, and content",
      example: "Try: 'Generate a logo for my startup'"
    },
    {
      icon: "🧠",
      title: "Learning & Adaptation",
      description: "Learns your preferences over time",
      example: "Suggests actions based on your patterns"
    },
    {
      icon: "🔧",
      title: "Self-Healing",
      description: "Automatically fixes issues and updates",
      example: "Detects and repairs system problems"
    },
    {
      icon: "🔒",
      title: "Privacy First",
      description: "All data stays on your device",
      example: "Full control over your information"
    }
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {features.map((feature, index) => (
          <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <span className="text-2xl">{feature.icon}</span>
              <div className="flex-1">
                <h4 className="font-medium text-gray-900 dark:text-white mb-1">
                  {feature.title}
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                  {feature.description}
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 italic">
                  {feature.example}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900 dark:to-purple-900 rounded-lg p-6 text-center">
        <h4 className="font-bold text-lg text-gray-900 dark:text-white mb-2">
          Ready to Get Started?
        </h4>
        <p className="text-gray-600 dark:text-gray-300">
          Your AI Assistant is configured and ready to help you be more productive!
        </p>
      </div>
    </div>
  );
};

// Complete Step Component
const CompleteStep: React.FC<any> = () => {
  return (
    <div className="text-center space-y-6">
      <div className="w-24 h-24 mx-auto bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
        <Check className="w-12 h-12 text-green-600 dark:text-green-400" />
      </div>

      <div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Welcome to Your AI Assistant!
        </h3>
        <p className="text-gray-600 dark:text-gray-300">
          Setup is complete. Your personal AI employee is ready to help.
        </p>
      </div>

      <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg p-6">
        <h4 className="font-bold mb-2">Quick Start Tips:</h4>
        <ul className="text-sm space-y-1 text-left max-w-md mx-auto">
          <li>• Use Ctrl+Shift+V for voice activation</li>
          <li>• Find me in your system tray</li>
          <li>• Try saying "Hello AI Assistant" to get started</li>
          <li>• Check the demo mode to see all features</li>
        </ul>
      </div>

      <div className="text-sm text-gray-500 dark:text-gray-400">
        You can change these settings anytime in the preferences menu.
      </div>
    </div>
  );
};

export default OnboardingWizard;