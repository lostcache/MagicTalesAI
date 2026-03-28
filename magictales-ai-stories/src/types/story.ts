export interface StoryCharacter {
  name: string;
  voiceTrait: "calm" | "deep" | "cheerful" | "high-pitched" | "gruff" | "gentle" | "wise" | "playful";
  emoji: string;
}

export interface StorySegment {
  speaker: string;
  emotion: "neutral" | "happy" | "sad" | "angry" | "scared" | "excited" | "calm" | "suspenseful";
  text: string;
}

export interface ProcessedStory {
  story_id: string;
  title: string;
  characters: StoryCharacter[];
  segments: StorySegment[];
  summary: string;
  learningInsights: string[];
}

export type PlayerState = "idle" | "processing" | "ready" | "playing" | "paused" | "asking" | "finished" | "recording";

export type VoiceMode = "ai" | "record";
