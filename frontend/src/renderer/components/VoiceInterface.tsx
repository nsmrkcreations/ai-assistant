import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import './VoiceInterface.css';

interface VoiceInterfaceProps {
  onTranscription?: (text: string) => void;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onError?: (error: string) => void;
}

const VoiceInterface: React.FC<VoiceInterfaceProps> = ({
  onTranscription,
  onSpeechStart,
  onSpeechEnd
}) => {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(true);
  const [continuousMode, setContinuousMode] = useState(false);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const webSocketRef = useRef<WebSocket | null>(null);
  
  const { sendMessage } = useWebSocket();

  useEffect(() => {
    // Check if browser supports required APIs
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setIsSupported(false);
      setError('Voice interface not supported in this browser');
    }

    // Initialize WebRTC connection for real-time audio streaming
    initializeWebRTC();

    return () => {
      cleanup();
    };
  }, []);

  const initializeWebRTC = useCallback(async () => {
    try {
      // This would set up WebRTC connection to backend for real-time streaming
      // For now, we'll use WebSocket for audio data transmission
      
    } catch (error) {
      console.error('WebRTC initialization failed:', error);
    }
  }, []);

  const cleanup = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    if (webSocketRef.current) {
      webSocketRef.current.close();
    }
  }, []);

  const startListening = useCallback(async () => {
    if (!isSupported || isListening) return;

    try {
      setError(null);
      setIsListening(true);
      onSpeechStart?.();

      // Get microphone access with optimal settings for speech recognition
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1
        }
      });
      
      streamRef.current = stream;

      // Set up audio context for visualization and processing
      audioContextRef.current = new AudioContext({ sampleRate: 16000 });
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      analyserRef.current.smoothingTimeConstant = 0.8;
      source.connect(analyserRef.current);

      // Start audio level monitoring
      monitorAudioLevel();

      // Set up MediaRecorder with optimal settings
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 16000
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await processAudio(audioBlob);
      };

      // Start recording with small time slices for real-time processing
      mediaRecorder.start(continuousMode ? 100 : 1000);

    } catch (err) {
      console.error('Error starting voice recording:', err);
      setError('Failed to access microphone');
      setIsListening(false);
    }
  }, [isSupported, isListening, onSpeechStart, continuousMode]);

  const stopListening = useCallback(() => {
    if (!isListening) return;

    setIsListening(false);
    onSpeechEnd?.();

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    setAudioLevel(0);
  }, [isListening, onSpeechEnd]);

  const monitorAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    
    const updateLevel = () => {
      if (!analyserRef.current || !isListening) return;
      
      analyserRef.current.getByteFrequencyData(dataArray);
      
      // Calculate average volume with emphasis on speech frequencies
      const speechFreqStart = Math.floor(dataArray.length * 0.1); // ~1.6kHz
      const speechFreqEnd = Math.floor(dataArray.length * 0.6);   // ~9.6kHz
      
      let speechSum = 0;
      for (let i = speechFreqStart; i < speechFreqEnd; i++) {
        speechSum += dataArray[i];
      }
      
      const speechAverage = speechSum / (speechFreqEnd - speechFreqStart);
      const normalizedLevel = Math.min(speechAverage / 128, 1);
      
      setAudioLevel(normalizedLevel);
      
      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };
    
    updateLevel();
  }, [isListening]);

  const processAudio = useCallback(async (audioBlob: Blob) => {
    try {
      setIsProcessing(true);
      
      // Convert blob to array buffer
      const arrayBuffer = await audioBlob.arrayBuffer();
      const audioData = new Uint8Array(arrayBuffer);
      
      // Convert audio data to base64 string
      const base64Audio = btoa(String.fromCharCode(...audioData));
      
      // Send audio data to backend for transcription
      const response = await sendMessage({
        message: 'transcribe_audio',
        include_audio: true,
        audio_data: base64Audio
      });
      
      if (response.transcription && response.transcription.trim()) {
        onTranscription?.(response.transcription);
        
        // In continuous mode, restart listening after processing
        if (continuousMode && !isListening) {
          setTimeout(() => startListening(), 100);
        }
      }
      
    } catch (err) {
      console.error('Error processing audio:', err);
      setError('Failed to process audio');
    } finally {
      setIsProcessing(false);
    }
  }, [sendMessage, onTranscription, continuousMode, isListening, startListening]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  const toggleContinuousMode = useCallback(() => {
    setContinuousMode(!continuousMode);
    if (isListening) {
      stopListening();
    }
  }, [continuousMode, isListening, stopListening]);

  // Voice activation detection
  useEffect(() => {
    if (continuousMode && !isListening && !isProcessing && audioLevel > 0.3) {
      startListening();
    }
  }, [continuousMode, isListening, isProcessing, audioLevel, startListening]);

  if (!isSupported) {
    return (
      <div className="voice-interface voice-interface--unsupported">
        <div className="voice-interface__error">
          Voice interface not supported in this browser
        </div>
      </div>
    );
  }

  return (
    <div className="voice-interface">
      <div className="voice-interface__controls">
        <button
          className={`voice-interface__button ${
            isListening ? 'voice-interface__button--listening' : ''
          } ${
            isProcessing ? 'voice-interface__button--processing' : ''
          }`}
          onClick={toggleListening}
          disabled={isProcessing}
          title={isListening ? 'Stop listening' : 'Start voice input'}
        >
          <div className="voice-interface__icon">
            {isProcessing ? (
              <div className="voice-interface__spinner" />
            ) : (
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
                <path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" />
              </svg>
            )}
          </div>
          
          {isListening && (
            <div 
              className="voice-interface__level"
              style={{
                transform: `scale(${1 + audioLevel * 0.5})`,
                opacity: 0.3 + audioLevel * 0.7
              }}
            />
          )}
        </button>
        
        <button
          className={`voice-interface__toggle ${
            continuousMode ? 'voice-interface__toggle--active' : ''
          }`}
          onClick={toggleContinuousMode}
          title="Toggle continuous listening mode"
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </button>
      </div>
      
      <div className="voice-interface__status">
        {isProcessing && (
          <span className="voice-interface__status-text">
            Processing...
          </span>
        )}
        {isListening && !isProcessing && (
          <span className="voice-interface__status-text">
            {continuousMode ? 'Continuous listening...' : 'Listening...'}
          </span>
        )}
        {continuousMode && !isListening && !isProcessing && (
          <span className="voice-interface__status-text">
            Voice activation ready
          </span>
        )}
        {error && (
          <span className="voice-interface__status-text voice-interface__status-text--error">
            {error}
          </span>
        )}
      </div>
      
      {/* Audio level indicator */}
      <div className="voice-interface__visualizer">
        <div className="voice-interface__level-bars">
          {Array.from({ length: 5 }, (_, i) => (
            <div
              key={i}
              className="voice-interface__level-bar"
              style={{
                height: `${Math.max(10, (audioLevel * 100) - (i * 15))}%`,
                opacity: audioLevel > (i * 0.2) ? 1 : 0.3
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default VoiceInterface;