import type { StoryCharacter } from "@/types/story";

const VOICE_LABELS: Record<string, string> = {
  calm: "Calm & Soothing",
  deep: "Deep & Strong",
  cheerful: "Cheerful & Bright",
  "high-pitched": "High & Squeaky",
  gruff: "Gruff & Rough",
  gentle: "Gentle & Soft",
  wise: "Wise & Warm",
  playful: "Playful & Fun",
};

interface CharacterPanelProps {
  characters: StoryCharacter[];
  activeCharacter?: string;
}

const CharacterPanel = ({ characters, activeCharacter }: CharacterPanelProps) => {
  return (
    <div className="space-y-3">
      <h3 className="font-display font-bold text-lg text-foreground">
        Characters
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {characters.filter(c => c.name.toLowerCase() !== "narrator").map((char) => (
          <div
            key={char.name}
            className={`flex items-center gap-3 p-3 rounded-lg border transition-all duration-300 ${
              activeCharacter?.toLowerCase() === char.name.toLowerCase()
                ? "border-primary bg-primary/10 shadow-md shadow-primary/10"
                : "border-border bg-card hover:border-primary/30"
            }`}
          >
            <span className="text-2xl">{char.emoji}</span>
            <div className="min-w-0">
              <p className="font-display font-bold text-sm text-foreground truncate">
                {char.name}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {VOICE_LABELS[char.voiceTrait] || char.voiceTrait}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CharacterPanel;
