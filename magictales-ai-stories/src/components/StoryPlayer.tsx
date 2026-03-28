import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Play } from "lucide-react";
import CharacterPanel from "@/components/CharacterPanel";
import VoiceModeSelector from "@/components/VoiceModeSelector";
import InteractivePlayer from "@/components/InteractivePlayer";
import type { ProcessedStory, VoiceMode } from "@/types/story";

interface StoryPlayerProps {
  story: ProcessedStory;
}

const StoryPlayer = ({ story }: StoryPlayerProps) => {
  const [started, setStarted] = useState(false);
  const [voiceMode, setVoiceMode] = useState<VoiceMode>("ai");
  const [voiceSample, setVoiceSample] = useState<string | null>(null);

  if (started) {
    return (
      <InteractivePlayer
        story={story}
        voiceMode={voiceMode}
        voiceSample={voiceSample}
        onStop={() => setStarted(false)}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Voice Mode Selector */}
      <VoiceModeSelector
        voiceMode={voiceMode}
        onModeChange={setVoiceMode}
        voiceSample={voiceSample}
        onVoiceSampleChange={setVoiceSample}
        story={story}
      />

      {/* Character Panel */}
      <div className="bg-card rounded-2xl border border-border p-6 shadow-sm">
        <CharacterPanel
          characters={story.characters}
          activeCharacter={undefined}
        />
      </div>

      {/* Start To Play */}
      <Button
        variant="magic"
        size="lg"
        className="w-full text-lg py-6"
        onClick={() => setStarted(true)}
      >
        <Play className="w-5 h-5" />
        Start To Play
      </Button>
    </div>
  );
};

export default StoryPlayer;
