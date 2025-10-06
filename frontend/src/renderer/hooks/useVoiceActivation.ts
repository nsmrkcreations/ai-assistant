import { useEffect, useCallback, useRef, useState } from 'react';

interface VoiceActivationOptions {
  hotkey?: string;
  pushToTalk?: boolean;
  voiceActivationThreshold?: number;
  onActivate?: () => void;
  onDeactivate?: () => void;
  onError?: (error: string) => void;
}

interface VoiceActivationState {
  isActive: boolean;
  isListening: boolean;
  audioLevel: number;
  error: string | null;
}

export const useVoiceActivation = (options: VoiceActivationOptions = {}) => {
  const {
    hotkey = 'ctrl+shift+v',
    pushToTalk = false,
    voiceActivationThreshold = 0.3,
    onActivate,
    onDeactivate,
    onError
  } = options;

  const [state, setState] = useState<VoiceActivationState>({
    isActive: false,
    isListening: false,
    audioLevel: 0,
    error: null
  });

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const hotkeyPressedRef = useRef(false);

  // Parse hotkey combination
  const parseHotkey = useCallback((hotkey: string) => {
    const keys = hotkey.toLowerCase().split('+');
    return {
      ctrl: keys.includes('ctrl'),
      shift: keys.includes('shift'),
      alt: keys.includes('alt'),
      meta: keys.includes('meta') || keys.includes('cmd'),
      key: keys[keys.length - 1]
    };
  }, []);

  // Check if hotkey matches current key event
  const matchesHotkey = useCallback((event: KeyboardEvent, hotkeyConfig: any) => {
    return (
      event.ctrlKey === hotkeyConfig.ctrl &&
      event.shiftKey === hotkeyConfig.shift &&
      event.altKey === hotkeyConfig.alt &&
      event.metaKey === hotkeyConfig.meta &&
      event.key.toLowerCase() === hotkeyConfig.key
    );
  }, []);

  // Initialize audio monitoring
  const initializeAudioMonitoring = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      streamRef.current = stream;
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      
      analyserRef.current.fftSize = 256;
      analyserRef.current.smoothingTimeConstant = 0.8;

      startAudioLevelMonitoring();

    } catch (error) {
      const errorMessage = `Failed to initialize audio monitoring: ${error}`;
      setState(prev => ({ ...prev, error: errorMessage }));
      onError?.(errorMessage);
    }
  }, [onError]);

  // Start monitoring audio levels
  const startAudioLevelMonitoring = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    
    const updateLevel = () => {
      if (!analyserRef.current) return;
      
      analyserRef.current.getByteFrequencyData(dataArray);
      
      // Calculate RMS energy focusing on speech frequencies
      const speechStart = Math.floor(dataArray.length * 0.1);
      const speechEnd = Math.floor(dataArray.length * 0.6);
      
      let sum = 0;
      for (let i = speechStart; i < speechEnd; i++) {
        sum += dataArray[i] * dataArray[i];
      }
      
      const rms = Math.sqrt(sum / (speechEnd - speechStart));
      const normalizedLevel = Math.min(rms / 128, 1);
      
      setState(prev => ({ ...prev, audioLevel: normalizedLevel }));
      
      // Voice activation detection
      if (!pushToTalk && normalizedLevel > voiceActivationThreshold && !state.isActive) {
        activateVoice();
      } else if (!pushToTalk && normalizedLevel < voiceActivationThreshold * 0.5 && state.isActive) {
        // Add some hysteresis to prevent rapid on/off switching
        setTimeout(() => {
          if (state.audioLevel < voiceActivationThreshold * 0.5) {
            deactivateVoice();
          }
        }, 1000);
      }
      
      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };
    
    updateLevel();
  }, [pushToTalk, voiceActivationThreshold, state.isActive, state.audioLevel]);

  // Activate voice input
  const activateVoice = useCallback(() => {
    setState(prev => ({ ...prev, isActive: true }));
    onActivate?.();
  }, [onActivate]);

  // Deactivate voice input
  const deactivateVoice = useCallback(() => {
    setState(prev => ({ ...prev, isActive: false }));
    onDeactivate?.();
  }, [onDeactivate]);

  // Handle keyboard events for hotkey detection
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const hotkeyConfig = parseHotkey(hotkey);
    
    if (matchesHotkey(event, hotkeyConfig)) {
      event.preventDefault();
      
      if (pushToTalk && !hotkeyPressedRef.current) {
        hotkeyPressedRef.current = true;
        activateVoice();
      } else if (!pushToTalk) {
        // Toggle mode for non-push-to-talk
        if (state.isActive) {
          deactivateVoice();
        } else {
          activateVoice();
        }
      }
    }
  }, [hotkey, pushToTalk, state.isActive, parseHotkey, matchesHotkey, activateVoice, deactivateVoice]);

  const handleKeyUp = useCallback((event: KeyboardEvent) => {
    const hotkeyConfig = parseHotkey(hotkey);
    
    if (matchesHotkey(event, hotkeyConfig) && pushToTalk && hotkeyPressedRef.current) {
      event.preventDefault();
      hotkeyPressedRef.current = false;
      deactivateVoice();
    }
  }, [hotkey, pushToTalk, parseHotkey, matchesHotkey, deactivateVoice]);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
  }, []);

  // Initialize and setup event listeners
  useEffect(() => {
    // Add global keyboard event listeners
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
    
    // Initialize audio monitoring if not in push-to-talk mode
    if (!pushToTalk) {
      initializeAudioMonitoring();
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('keyup', handleKeyUp);
      cleanup();
    };
  }, [handleKeyDown, handleKeyUp, pushToTalk, initializeAudioMonitoring, cleanup]);

  // Manual control functions
  const startListening = useCallback(async () => {
    if (!streamRef.current) {
      await initializeAudioMonitoring();
    }
    setState(prev => ({ ...prev, isListening: true }));
  }, [initializeAudioMonitoring]);

  const stopListening = useCallback(() => {
    setState(prev => ({ ...prev, isListening: false }));
    cleanup();
  }, [cleanup]);

  const toggleListening = useCallback(() => {
    if (state.isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [state.isListening, startListening, stopListening]);

  return {
    ...state,
    startListening,
    stopListening,
    toggleListening,
    activateVoice,
    deactivateVoice
  };
};