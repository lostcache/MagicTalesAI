import { useCallback, useEffect, useRef, useState } from "react";
import type { StoryCharacter, StorySegment } from "@/types/story";

// Map voice traits to speech synthesis settings
const VOICE_SETTINGS: Record<string, { pitch: number; rate: number }> = {
  calm: { pitch: 1.0, rate: 0.9 },
  deep: { pitch: 0.6, rate: 0.85 },
  cheerful: { pitch: 1.3, rate: 1.05 },
  "high-pitched": { pitch: 1.6, rate: 1.1 },
  gruff: { pitch: 0.5, rate: 0.8 },
  gentle: { pitch: 1.1, rate: 0.85 },
  wise: { pitch: 0.9, rate: 0.8 },
  playful: { pitch: 1.4, rate: 1.1 },
};

export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(-1);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const segmentsRef = useRef<StorySegment[]>([]);
  const charactersRef = useRef<StoryCharacter[]>([]);
  const onFinishRef = useRef<(() => void) | null>(null);
  const pausedRef = useRef(false);

  // Get available voices, preferring English ones
  const getVoice = useCallback((index: number) => {
    const voices = speechSynthesis.getVoices();
    const englishVoices = voices.filter((v) => v.lang.startsWith("en"));
    if (englishVoices.length === 0) return voices[0] || null;
    // Rotate through available voices for different characters
    return englishVoices[index % englishVoices.length];
  }, []);

  const speakSegment = useCallback(
    (index: number) => {
      const segments = segmentsRef.current;
      const characters = charactersRef.current;

      if (index >= segments.length) {
        setIsSpeaking(false);
        setCurrentSegmentIndex(-1);
        onFinishRef.current?.();
        return;
      }

      const segment = segments[index];
      const character = characters.find(
        (c) => c.name.toLowerCase() === segment.speaker.toLowerCase()
      );
      const settings = VOICE_SETTINGS[character?.voiceTrait || "calm"];

      const utterance = new SpeechSynthesisUtterance(segment.text);
      utterance.pitch = settings.pitch;
      utterance.rate = settings.rate;
      utterance.volume = 1;

      // Assign different voices to different characters
      const charIndex = character
        ? characters.indexOf(character)
        : characters.length;
      const voice = getVoice(charIndex);
      if (voice) utterance.voice = voice;

      utterance.onend = () => {
        if (!pausedRef.current) {
          speakSegment(index + 1);
        }
      };

      utterance.onerror = (e) => {
        console.error("Speech error:", e);
        if (!pausedRef.current) {
          speakSegment(index + 1);
        }
      };

      utteranceRef.current = utterance;
      setCurrentSegmentIndex(index);
      speechSynthesis.speak(utterance);
    },
    [getVoice]
  );

  const play = useCallback(
    (
      segments: StorySegment[],
      characters: StoryCharacter[],
      startIndex = 0,
      onFinish?: () => void
    ) => {
      speechSynthesis.cancel();
      segmentsRef.current = segments;
      charactersRef.current = characters;
      onFinishRef.current = onFinish || null;
      pausedRef.current = false;
      setIsSpeaking(true);
      speakSegment(startIndex);
    },
    [speakSegment]
  );

  const pause = useCallback(() => {
    pausedRef.current = true;
    speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  const resume = useCallback(() => {
    if (currentSegmentIndex >= 0) {
      pausedRef.current = false;
      setIsSpeaking(true);
      speakSegment(currentSegmentIndex);
    }
  }, [currentSegmentIndex, speakSegment]);

  const stop = useCallback(() => {
    pausedRef.current = true;
    speechSynthesis.cancel();
    setIsSpeaking(false);
    setCurrentSegmentIndex(-1);
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      speechSynthesis.cancel();
    };
  }, []);

  return {
    isSpeaking,
    currentSegmentIndex,
    play,
    pause,
    resume,
    stop,
    totalSegments: segmentsRef.current.length,
  };
}
