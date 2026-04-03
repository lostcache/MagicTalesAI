import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Loader2, ArrowLeft, Upload, BookOpen, Play } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import StoryPlayer from "@/components/StoryPlayer";
import type { ProcessedStory } from "@/types/story";
import { Link } from "react-router-dom";

interface StoryMeta {
  story_id: string;
  filename: string;
  created_at: string;
  status: string;
}

const GEMINI_VOICE_TO_TRAIT: Record<string, StoryCharacter["voiceTrait"]> = {
  Puck: "playful",
  Charon: "deep",
  Kore: "gentle",
  Fenrir: "gruff",
  Aoede: "calm",
  Leda: "cheerful",
  Orus: "wise",
  Zephyr: "cheerful",
};

const ROLE_TO_EMOJI: Record<string, string> = {
  protagonist: "🦸",
  antagonist: "🦹",
  supporting: "👤",
  narrator: "📖",
};

const buildProcessedStory = (data: {
  story_id: string; filename: string;
  characters: { name: string; role: string }[];
  segments: { speaker: string; emotion: string; text: string }[];
  voice_assignments?: { character_name: string; voice_name: string }[] | null;
}): ProcessedStory => {
  const title = (data.filename || "untitled").replace(/\.[^/.]+$/, "") || "Your Story";
  return {
    story_id: data.story_id,
    title,
    characters: data.characters.map((c) => {
      const assignment = (data.voice_assignments ?? []).find(
        (a) => a.character_name.toLowerCase() === c.name.toLowerCase()
      );
      return {
        name: c.name,
        voiceTrait: GEMINI_VOICE_TO_TRAIT[assignment?.voice_name ?? ""] ?? "calm",
        emoji: ROLE_TO_EMOJI[c.role] ?? "👤",
      };
    }),
    segments: data.segments.map((s) => ({
      speaker: s.speaker,
      emotion: s.emotion as ProcessedStory["segments"][number]["emotion"],
      text: s.text,
    })),
    summary: "",
    learningInsights: [],
  };
};

const CreateAudiobook = () => {
  const [storyText, setStoryText] = useState("");
  const [filename, setFilename] = useState("untitled");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedStory, setProcessedStory] = useState<ProcessedStory | null>(null);
  const [mode, setMode] = useState<"select" | "custom" | "player">("select");
  const [savedStories, setSavedStories] = useState<StoryMeta[]>([]);
  const [loadingStoryId, setLoadingStoryId] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    fetch("/api/stories")
      .then((r) => r.json())
      .then((list) => setSavedStories(list))
      .catch(() => {
        toast({ variant: "destructive", title: "Backend unavailable", description: "Could not load saved stories. Is the server running?" });
      });
  }, []);

  const processStory = async (text: string, name = filename) => {
    setIsProcessing(true);
    try {
      // Step 1: extract characters and segments
      const extractRes = await fetch("/api/extract-characters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, filename: name }),
      });
      if (!extractRes.ok) throw new Error(await extractRes.text());
      const extracted = await extractRes.json();
      const { story_id, characters, segments } = extracted;

      // Step 2: assign voices
      const voiceRes = await fetch(`/api/stories/${story_id}/assign-voices`, {
        method: "POST",
      });
      if (!voiceRes.ok) throw new Error(await voiceRes.text());
      const { assignments } = await voiceRes.json();

      // Step 3: kick off music generation (fire-and-forget)
      fetch(`/api/stories/${story_id}/generate-music`, { method: "POST" }).catch(() => {});

      const story = buildProcessedStory({ story_id, filename: name, characters, segments, voice_assignments: assignments });
      setProcessedStory(story);
      setMode("player");
      // Refresh list so newly processed story appears
      fetch("/api/stories").then((r) => r.json()).then(setSavedStories).catch(() => {});
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Could not process the story. Please try again.";
      console.error("Process error:", e);
      toast({
        variant: "destructive",
        title: "Processing Failed",
        description: message,
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const openSavedStory = async (storyId: string) => {
    setLoadingStoryId(storyId);
    try {
      const res = await fetch(`/api/stories/${storyId}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setProcessedStory(buildProcessedStory(data));
      setMode("player");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to load story.";
      toast({ variant: "destructive", title: "Load Failed", description: message });
    } finally {
      setLoadingStoryId(null);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const name = file.name.toLowerCase();
    const type = file.type;

    try {
      if (type === "text/plain" || name.endsWith(".txt")) {
        const text = await file.text();
        if (!text.trim()) {
          toast({ variant: "destructive", title: "Empty File", description: "Could not extract text from this file." });
          return;
        }
        setFilename(file.name);
        setStoryText(text);
        setMode("custom");
      } else if (name.endsWith(".epub") || name.endsWith(".pdf") || type === "application/epub+zip" || type === "application/pdf") {
        // Send to backend for server-side extraction
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch("/api/upload-text", { method: "POST", body: formData });
        if (!res.ok) {
          const body = await res.text().catch(() => "");
          throw new Error(`Upload failed (${res.status})${body ? ": " + body : ""}`);
        }
        const { text } = await res.json();
        if (!text?.trim()) {
          toast({ variant: "destructive", title: "Empty File", description: "Could not extract text from this file." });
          return;
        }
        setFilename(file.name);
        setStoryText(text);
        setMode("custom");
      } else {
        toast({ variant: "destructive", title: "Unsupported File", description: "Please upload a .txt, .epub, or .pdf file." });
      }
    } catch (err) {
      console.error("File parse error:", err);
      toast({ variant: "destructive", title: "Parse Error", description: "Failed to read the file. Try a different format." });
    }
  };

  if (isProcessing) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-6 animate-fade-up">
          <div className="w-20 h-20 mx-auto rounded-full flex items-center justify-center" style={{ background: "var(--gradient-magic)" }}>
            <Sparkles className="w-10 h-10 text-primary-foreground animate-sparkle" />
          </div>
          <div>
            <h2 className="font-display font-extrabold text-2xl text-foreground mb-2">
              Creating Your Audiobook...
            </h2>
            <p className="font-body text-muted-foreground">
              AI is extracting characters, emotions, and building your story ✨
            </p>
          </div>
          <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin" />
        </div>
      </div>
    );
  }

  if (mode === "player" && processedStory) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8 max-w-3xl">
          <div className="flex items-center gap-3 mb-8">
            <Button variant="outline" size="sm" onClick={() => setMode("select")} asChild>
              <Link to="/create">
                <ArrowLeft className="w-4 h-4" />
                New Story
              </Link>
            </Button>
            <h1 className="font-display font-extrabold text-2xl text-foreground">
              Now Playing
            </h1>
          </div>
          <StoryPlayer story={processedStory} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-3xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Button variant="outline" size="sm" asChild>
            <Link to="/">
              <ArrowLeft className="w-4 h-4" />
              Home
            </Link>
          </Button>
          <h1 className="font-display font-extrabold text-2xl text-foreground">
            Create Audiobook
          </h1>
        </div>

        {mode === "select" && (
          <div className="space-y-8 animate-fade-up">
            {/* Pick a Story */}
            <div>
              <h2 className="font-display font-bold text-lg text-foreground mb-4">
                Pick a Story
              </h2>
              {savedStories.length === 0 ? (
                <p className="text-sm text-muted-foreground font-body">No stories yet — upload one below.</p>
              ) : (
                <div className="grid gap-3">
                  {savedStories.map((s) => (
                    <button
                      key={s.story_id}
                      onClick={() => openSavedStory(s.story_id)}
                      disabled={loadingStoryId === s.story_id}
                      className="flex items-center gap-4 p-4 rounded-2xl border border-border bg-card hover:border-primary/50 hover:shadow-md hover:shadow-primary/5 transition-all text-left group"
                    >
                      <span className="text-3xl group-hover:scale-110 transition-transform">
                        <BookOpen className="w-8 h-8 text-primary/60" />
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-display font-bold text-foreground truncate">
                          {s.filename.replace(/\.[^/.]+$/, "") || "Untitled"}
                        </p>
                        <p className="text-xs text-muted-foreground font-body capitalize">
                          {s.status.replace(/_/g, " ")} · {new Date(s.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      {loadingStoryId === s.story_id
                        ? <Loader2 className="w-5 h-5 text-primary animate-spin" />
                        : <Play className="w-5 h-5 text-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                      }
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="flex items-center gap-4">
              <div className="flex-1 h-px bg-border" />
              <span className="text-sm text-muted-foreground font-body">or</span>
              <div className="flex-1 h-px bg-border" />
            </div>

            {/* Upload */}
            <Button variant="outline" size="lg" className="w-full relative" asChild>
              <label>
                <Upload className="w-5 h-5" />
                Upload
                <input
                  type="file"
                  accept=".txt,.epub,.pdf,text/plain,application/epub+zip,application/pdf"
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  onChange={handleFileUpload}
                />
              </label>
            </Button>
          </div>
        )}

        {mode === "custom" && (
          <div className="space-y-4 animate-fade-up">
            <div className="flex items-center justify-between">
              <h2 className="font-display font-bold text-lg text-foreground">
                ✍️ Paste or Write Your Story
              </h2>
              <Button variant="ghost" size="sm" onClick={() => setMode("select")}>
                ← Back
              </Button>
            </div>
            <Textarea
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
              placeholder="Once upon a time..."
              className="min-h-[300px] font-body text-base"
            />
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground font-body">
                {storyText.length} / 20,000 characters
              </p>
              <Button
                variant="magic"
                size="lg"
                onClick={() => processStory(storyText)}
                disabled={storyText.trim().length < 50}
              >
                <Sparkles className="w-5 h-5" />
                Generate Audiobook
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CreateAudiobook;
