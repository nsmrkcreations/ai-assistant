/**
 * Accessibility Provider for AI Assistant
 * Provides comprehensive accessibility features and ARIA support
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface AccessibilitySettings {
  highContrast: boolean;
  largeText: boolean;
  reducedMotion: boolean;
  screenReaderMode: boolean;
  keyboardNavigation: boolean;
  focusIndicators: boolean;
  colorBlindMode: 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia';
  fontSize: number;
  lineHeight: number;
}

interface AccessibilityContextType {
  settings: AccessibilitySettings;
  updateSettings: (settings: Partial<AccessibilitySettings>) => void;
  announceToScreenReader: (message: string, priority?: 'polite' | 'assertive') => void;
  focusElement: (elementId: string) => void;
  skipToContent: () => void;
}

const defaultSettings: AccessibilitySettings = {
  highContrast: false,
  largeText: false,
  reducedMotion: false,
  screenReaderMode: false,
  keyboardNavigation: true,
  focusIndicators: true,
  colorBlindMode: 'none',
  fontSize: 16,
  lineHeight: 1.5
};

const AccessibilityContext = createContext<AccessibilityContextType | null>(null);

export const useAccessibility = () => {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within AccessibilityProvider');
  }
  return context;
};

interface AccessibilityProviderProps {
  children: React.ReactNode;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({ children }) => {
  const [settings, setSettings] = useState<AccessibilitySettings>(defaultSettings);
  const [announcer, setAnnouncer] = useState<HTMLElement | null>(null);

  // Initialize accessibility features
  useEffect(() => {
    // Load saved settings
    const savedSettings = localStorage.getItem('accessibility-settings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setSettings({ ...defaultSettings, ...parsed });
      } catch (error) {
        console.error('Error loading accessibility settings:', error);
      }
    }

    // Detect system preferences
    detectSystemPreferences();

    // Create screen reader announcer
    createScreenReaderAnnouncer();

    // Setup keyboard navigation
    setupKeyboardNavigation();

    // Setup focus management
    setupFocusManagement();

  }, []);

  // Apply settings when they change
  useEffect(() => {
    applyAccessibilitySettings();
    localStorage.setItem('accessibility-settings', JSON.stringify(settings));
  }, [settings]);

  const detectSystemPreferences = () => {
    // Detect reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    // Detect high contrast preference
    const prefersHighContrast = window.matchMedia('(prefers-contrast: high)').matches;
    
    // Detect color scheme preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (prefersReducedMotion || prefersHighContrast) {
      setSettings(prev => ({
        ...prev,
        reducedMotion: prefersReducedMotion,
        highContrast: prefersHighContrast
      }));
    }
  };

  const createScreenReaderAnnouncer = () => {
    const announcer = document.createElement('div');
    announcer.id = 'screen-reader-announcer';
    announcer.setAttribute('aria-live', 'polite');
    announcer.setAttribute('aria-atomic', 'true');
    announcer.style.position = 'absolute';
    announcer.style.left = '-10000px';
    announcer.style.width = '1px';
    announcer.style.height = '1px';
    announcer.style.overflow = 'hidden';
    
    document.body.appendChild(announcer);
    setAnnouncer(announcer);
  };

  const setupKeyboardNavigation = () => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Skip to content with Alt+S
      if (event.altKey && event.key === 's') {
        event.preventDefault();
        skipToContent();
      }

      // Focus search with Ctrl+K
      if (event.ctrlKey && event.key === 'k') {
        event.preventDefault();
        focusElement('search-input');
      }

      // Toggle voice with Ctrl+Shift+V
      if (event.ctrlKey && event.shiftKey && event.key === 'V') {
        event.preventDefault();
        // Trigger voice activation
        window.dispatchEvent(new CustomEvent('toggle-voice'));
      }

      // Escape key handling
      if (event.key === 'Escape') {
        // Close modals, dropdowns, etc.
        window.dispatchEvent(new CustomEvent('escape-pressed'));
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  };

  const setupFocusManagement = () => {
    // Add focus indicators
    const style = document.createElement('style');
    style.textContent = `
      .focus-visible {
        outline: 2px solid #0066cc !important;
        outline-offset: 2px !important;
      }
      
      .skip-link {
        position: absolute;
        top: -40px;
        left: 6px;
        background: #000;
        color: #fff;
        padding: 8px;
        text-decoration: none;
        z-index: 1000;
        border-radius: 4px;
      }
      
      .skip-link:focus {
        top: 6px;
      }
    `;
    document.head.appendChild(style);

    // Add skip link
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'skip-link';
    skipLink.textContent = 'Skip to main content';
    skipLink.addEventListener('click', (e) => {
      e.preventDefault();
      skipToContent();
    });
    
    document.body.insertBefore(skipLink, document.body.firstChild);
  };

  const applyAccessibilitySettings = () => {
    const root = document.documentElement;

    // Apply high contrast
    if (settings.highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }

    // Apply large text
    if (settings.largeText) {
      root.classList.add('large-text');
    } else {
      root.classList.remove('large-text');
    }

    // Apply reduced motion
    if (settings.reducedMotion) {
      root.classList.add('reduced-motion');
    } else {
      root.classList.remove('reduced-motion');
    }

    // Apply color blind mode
    root.classList.remove('protanopia', 'deuteranopia', 'tritanopia');
    if (settings.colorBlindMode !== 'none') {
      root.classList.add(settings.colorBlindMode);
    }

    // Apply font size
    root.style.setProperty('--base-font-size', `${settings.fontSize}px`);
    root.style.setProperty('--base-line-height', settings.lineHeight.toString());

    // Apply CSS custom properties for accessibility
    const accessibilityStyles = `
      :root {
        --focus-color: ${settings.highContrast ? '#ffff00' : '#0066cc'};
        --focus-width: ${settings.focusIndicators ? '2px' : '0px'};
        --animation-duration: ${settings.reducedMotion ? '0s' : '0.3s'};
        --transition-duration: ${settings.reducedMotion ? '0s' : '0.2s'};
      }
      
      .high-contrast {
        --bg-primary: #000000;
        --text-primary: #ffffff;
        --bg-secondary: #1a1a1a;
        --text-secondary: #cccccc;
        --border-color: #ffffff;
        --accent-color: #ffff00;
      }
      
      .large-text {
        --base-font-size: ${Math.max(18, settings.fontSize)}px;
        --base-line-height: ${Math.max(1.6, settings.lineHeight)};
      }
      
      .reduced-motion * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
      }
      
      .protanopia {
        filter: url(#protanopia-filter);
      }
      
      .deuteranopia {
        filter: url(#deuteranopia-filter);
      }
      
      .tritanopia {
        filter: url(#tritanopia-filter);
      }
    `;

    // Update or create accessibility stylesheet
    let styleElement = document.getElementById('accessibility-styles');
    if (!styleElement) {
      styleElement = document.createElement('style');
      styleElement.id = 'accessibility-styles';
      document.head.appendChild(styleElement);
    }
    styleElement.textContent = accessibilityStyles;

    // Add color blind filters
    addColorBlindFilters();
  };

  const addColorBlindFilters = () => {
    let svg = document.getElementById('accessibility-filters');
    if (!svg) {
      svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.id = 'accessibility-filters';
      svg.style.position = 'absolute';
      svg.style.width = '0';
      svg.style.height = '0';
      document.body.appendChild(svg);
    }

    svg.innerHTML = `
      <defs>
        <filter id="protanopia-filter">
          <feColorMatrix type="matrix" values="0.567 0.433 0 0 0
                                               0.558 0.442 0 0 0
                                               0 0.242 0.758 0 0
                                               0 0 0 1 0"/>
        </filter>
        <filter id="deuteranopia-filter">
          <feColorMatrix type="matrix" values="0.625 0.375 0 0 0
                                               0.7 0.3 0 0 0
                                               0 0.3 0.7 0 0
                                               0 0 0 1 0"/>
        </filter>
        <filter id="tritanopia-filter">
          <feColorMatrix type="matrix" values="0.95 0.05 0 0 0
                                               0 0.433 0.567 0 0
                                               0 0.475 0.525 0 0
                                               0 0 0 1 0"/>
        </filter>
      </defs>
    `;
  };

  const updateSettings = useCallback((newSettings: Partial<AccessibilitySettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  }, []);

  const announceToScreenReader = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (announcer) {
      announcer.setAttribute('aria-live', priority);
      announcer.textContent = message;
      
      // Clear after announcement
      setTimeout(() => {
        announcer.textContent = '';
      }, 1000);
    }
  }, [announcer]);

  const focusElement = useCallback((elementId: string) => {
    const element = document.getElementById(elementId);
    if (element) {
      element.focus();
      announceToScreenReader(`Focused on ${element.getAttribute('aria-label') || elementId}`);
    }
  }, [announceToScreenReader]);

  const skipToContent = useCallback(() => {
    const mainContent = document.getElementById('main-content') || 
                       document.querySelector('main') ||
                       document.querySelector('[role="main"]');
    
    if (mainContent) {
      mainContent.focus();
      announceToScreenReader('Skipped to main content');
    }
  }, [announceToScreenReader]);

  const contextValue: AccessibilityContextType = {
    settings,
    updateSettings,
    announceToScreenReader,
    focusElement,
    skipToContent
  };

  return (
    <AccessibilityContext.Provider value={contextValue}>
      {children}
    </AccessibilityContext.Provider>
  );
};

// Accessibility Settings Component
export const AccessibilitySettings: React.FC = () => {
  const { settings, updateSettings } = useAccessibility();

  return (
    <div className="accessibility-settings" role="region" aria-labelledby="accessibility-heading">
      <h2 id="accessibility-heading">Accessibility Settings</h2>
      
      <div className="settings-group">
        <h3>Visual</h3>
        
        <label className="setting-item">
          <input
            type="checkbox"
            checked={settings.highContrast}
            onChange={(e) => updateSettings({ highContrast: e.target.checked })}
            aria-describedby="high-contrast-desc"
          />
          <span>High Contrast Mode</span>
          <p id="high-contrast-desc" className="setting-description">
            Increases contrast for better visibility
          </p>
        </label>

        <label className="setting-item">
          <input
            type="checkbox"
            checked={settings.largeText}
            onChange={(e) => updateSettings({ largeText: e.target.checked })}
            aria-describedby="large-text-desc"
          />
          <span>Large Text</span>
          <p id="large-text-desc" className="setting-description">
            Increases text size for better readability
          </p>
        </label>

        <div className="setting-item">
          <label htmlFor="font-size-slider">Font Size: {settings.fontSize}px</label>
          <input
            id="font-size-slider"
            type="range"
            min="12"
            max="24"
            value={settings.fontSize}
            onChange={(e) => updateSettings({ fontSize: parseInt(e.target.value) })}
            aria-describedby="font-size-desc"
          />
          <p id="font-size-desc" className="setting-description">
            Adjust base font size
          </p>
        </div>

        <div className="setting-item">
          <label htmlFor="color-blind-select">Color Blind Support</label>
          <select
            id="color-blind-select"
            value={settings.colorBlindMode}
            onChange={(e) => updateSettings({ colorBlindMode: e.target.value as any })}
            aria-describedby="color-blind-desc"
          >
            <option value="none">None</option>
            <option value="protanopia">Protanopia (Red-blind)</option>
            <option value="deuteranopia">Deuteranopia (Green-blind)</option>
            <option value="tritanopia">Tritanopia (Blue-blind)</option>
          </select>
          <p id="color-blind-desc" className="setting-description">
            Adjust colors for color vision deficiencies
          </p>
        </div>
      </div>

      <div className="settings-group">
        <h3>Motion & Animation</h3>
        
        <label className="setting-item">
          <input
            type="checkbox"
            checked={settings.reducedMotion}
            onChange={(e) => updateSettings({ reducedMotion: e.target.checked })}
            aria-describedby="reduced-motion-desc"
          />
          <span>Reduce Motion</span>
          <p id="reduced-motion-desc" className="setting-description">
            Minimizes animations and transitions
          </p>
        </label>
      </div>

      <div className="settings-group">
        <h3>Navigation</h3>
        
        <label className="setting-item">
          <input
            type="checkbox"
            checked={settings.keyboardNavigation}
            onChange={(e) => updateSettings({ keyboardNavigation: e.target.checked })}
            aria-describedby="keyboard-nav-desc"
          />
          <span>Enhanced Keyboard Navigation</span>
          <p id="keyboard-nav-desc" className="setting-description">
            Enables additional keyboard shortcuts and navigation aids
          </p>
        </label>

        <label className="setting-item">
          <input
            type="checkbox"
            checked={settings.focusIndicators}
            onChange={(e) => updateSettings({ focusIndicators: e.target.checked })}
            aria-describedby="focus-indicators-desc"
          />
          <span>Focus Indicators</span>
          <p id="focus-indicators-desc" className="setting-description">
            Shows clear focus indicators for keyboard navigation
          </p>
        </label>

        <label className="setting-item">
          <input
            type="checkbox"
            checked={settings.screenReaderMode}
            onChange={(e) => updateSettings({ screenReaderMode: e.target.checked })}
            aria-describedby="screen-reader-desc"
          />
          <span>Screen Reader Mode</span>
          <p id="screen-reader-desc" className="setting-description">
            Optimizes interface for screen readers
          </p>
        </label>
      </div>

      <div className="keyboard-shortcuts">
        <h3>Keyboard Shortcuts</h3>
        <dl>
          <dt>Alt + S</dt>
          <dd>Skip to main content</dd>
          
          <dt>Ctrl + K</dt>
          <dd>Focus search</dd>
          
          <dt>Ctrl + Shift + V</dt>
          <dd>Toggle voice activation</dd>
          
          <dt>Escape</dt>
          <dd>Close modals and dropdowns</dd>
        </dl>
      </div>
    </div>
  );
};

export default AccessibilityProvider;