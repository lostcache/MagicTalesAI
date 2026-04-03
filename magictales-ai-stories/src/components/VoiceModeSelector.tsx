import { useState, useCallback, useRef } from "react";
import { Mic, MicOff, Sparkles, Upload, Trash2, Play, Square, Loader2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { VoiceMode, ProcessedStory } from "@/types/story";

interface VoiceModeSelectorProps {
  voiceMode: VoiceMode;
  onModeChange: (mode: VoiceMode) => void;
  voiceSample: string | null;
  onVoiceSampleChange: (sample: string | null) => void;
  story: ProcessedStory;
}

const VoiceModeSelector = ({ voiceMode, onModeChange, voiceSample, onVoiceSampleChange, story }: VoiceModeSelectorProps) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [cloneState, setCloneState] = useState<"idle" | "cloning" | "done">("idle");
  const [clonedVoiceId, setClonedVoiceId] = useState<string | null>(null);
  const [cloneMsg, setCloneMsg] = useState("");
  const [assignedChars, setAssignedChars] = useState<Record<string, boolean>>({});
  const [assigningChar, setAssigningChar] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        onVoiceSampleChange(url);
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch {
      setCloneMsg("Microphone access denied.");
    }
  }, [onVoiceSampleChange]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, []);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    onVoiceSampleChange(url);
  }, [onVoiceSampleChange]);

  const handlePlaySample = useCallback(() => {
    if (!voiceSample) return;
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      return;
    }
    const audio = new Audio(voiceSample);
    audioRef.current = audio;
    audio.onended = () => setIsPlaying(false);
    audio.play();
    setIsPlaying(true);
  }, [voiceSample, isPlaying]);

  const handleRemoveSample = useCallback(() => {
    onVoiceSampleChange(null);
    setCloneState("idle");
    setClonedVoiceId(null);
    setCloneMsg("");
    setAssignedChars({});
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, [onVoiceSampleChange]);

  const handleCloneVoice = useCallback(async () => {
    if (!voiceSample) return;
    setCloneState("cloning");
    setCloneMsg("");
    try {
      const blob = await fetch(voiceSample).then((r) => r.blob());
      const fd = new FormData();
      fd.append("files", blob, "recording.webm");

      const res = await fetch("/api/voices/clone", { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setClonedVoiceId(data.voice_id);
      setCloneState("done");
      const note = data.requires_verification
        ? " ElevenLabs may require account verification before this voice is usable."
        : "";
      setCloneMsg(`Voice "${data.name}" cloned.${note}`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Clone failed";
      setCloneMsg(`Clone failed: ${msg}`);
      setCloneState("idle");
    }
  }, [voiceSample]);

  const handleAssignVoice = useCallback(async (characterName: string) => {
    if (!clonedVoiceId || !story.story_id) return;
    setAssigningChar(characterName);
    try {
      const res = await fetch(`/api/stories/${story.story_id}/assign-custom-voice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ character_name: characterName, elevenlabs_voice_id: clonedVoiceId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      setAssignedChars((prev) => ({ ...prev, [characterName]: true }));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Assignment failed";
      setCloneMsg(`Assignment failed: ${msg}`);
    } finally {
      setAssigningChar(null);
    }
  }, [clonedVoiceId, story.story_id]);

  return (
    <div className="bg-card rounded-2xl border border-border p-6 shadow-sm">
      <h3 className="font-display font-bold text-lg text-foreground mb-3">
        Character Voices
      </h3>
      <p className="text-sm text-muted-foreground font-body mb-4">
        Use AI voices for all characters, or clone your own voice and assign it to any character you choose.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          onClick={() => onModeChange("record")}
          className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all text-left ${
            voiceMode === "record"
              ? "border-primary bg-primary/10 shadow-md shadow-primary/10"
              : "border-border bg-card hover:border-primary/30"
          }`}
        >
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <Mic className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="font-display font-bold text-sm text-foreground">My Voice</p>
            <p className="text-xs text-muted-foreground">Clone your voice, assign to any character</p>
          </div>
        </button>

        <button
          onClick={() => onModeChange("ai")}
          className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all text-left ${
            voiceMode === "ai"
              ? "border-primary bg-primary/10 shadow-md shadow-primary/10"
              : "border-border bg-card hover:border-primary/30"
          }`}
        >
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="font-display font-bold text-sm text-foreground">AI Voice</p>
            <p className="text-xs text-muted-foreground">AI reads the story for you</p>
          </div>
        </button>
      </div>

      {voiceMode === "record" && (
        <div className="mt-4 space-y-4 animate-fade-up">
          {/* Step 1: Record / upload sample */}
          <div className="p-4 rounded-xl border border-border bg-muted/30 space-y-3">
            <p className="font-display font-bold text-sm text-foreground">1 · VOICE SAMPLE</p>

            {voiceSample ? (
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={handlePlaySample}>
                  {isPlaying ? <Square className="w-4 h-4 mr-1" /> : <Play className="w-4 h-4 mr-1" />}
                  {isPlaying ? "Stop" : "Preview"}
                </Button>
                <span className="text-xs text-muted-foreground font-body flex-1">✅ Sample ready</span>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleRemoveSample}>
                  <Trash2 className="w-4 h-4 text-destructive" />
                </Button>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Button variant="default" size="sm" className="relative" asChild>
                  <label>
                    <Upload className="w-4 h-4 mr-1" />
                    Upload recording
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="audio/*"
                      className="absolute inset-0 opacity-0 cursor-pointer"
                      onChange={handleFileUpload}
                    />
                  </label>
                </Button>

                {isRecording ? (
                  <Button variant="destructive" size="sm" onClick={stopRecording}>
                    <MicOff className="w-4 h-4 mr-1" />
                    Stop Recording
                  </Button>
                ) : (
                  <Button variant="outline" size="sm" onClick={startRecording}>
                    <Mic className="w-4 h-4 mr-1" />
                    Record from mic
                  </Button>
                )}
              </div>
            )}
            <p className="text-xs text-muted-foreground font-body">
              1+ minutes of clean speech recommended. Short clips may work but quality varies.
            </p>
          </div>

          {/* Step 2: Clone voice */}
          {voiceSample && (
            <div className="p-4 rounded-xl border border-border bg-muted/30 space-y-3 animate-fade-up">
              <p className="font-display font-bold text-sm text-foreground">2 · CLONE VOICE</p>
              {cloneState === "done" ? (
                <p className="text-xs text-green-600 font-body">{cloneMsg}</p>
              ) : (
                <>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleCloneVoice}
                    disabled={cloneState === "cloning"}
                  >
                    {cloneState === "cloning" ? (
                      <><Loader2 className="w-4 h-4 mr-1 animate-spin" />Cloning…</>
                    ) : (
                      <><Sparkles className="w-4 h-4 mr-1" />Clone with ElevenLabs</>
                    )}
                  </Button>
                  {cloneMsg && <p className="text-xs text-destructive font-body">{cloneMsg}</p>}
                </>
              )}
            </div>
          )}

          {/* Step 3: Assign to characters */}
          {cloneState === "done" && (
            <div className="p-4 rounded-xl border border-border bg-muted/30 space-y-3 animate-fade-up">
              <p className="font-display font-bold text-sm text-foreground">3 · ASSIGN TO CHARACTERS</p>
              <p className="text-xs text-muted-foreground font-body">
                Assign your cloned voice to one or more characters. Unassigned characters keep their AI voices.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {story.characters.map((char) => (
                  <div key={char.name} className="flex items-center justify-between p-3 rounded-lg border border-border bg-card">
                    <span className="flex items-center gap-2 text-sm font-body">
                      <span>{char.emoji}</span>
                      <span className="font-display font-bold text-foreground">{char.name}</span>
                    </span>
                    {assignedChars[char.name] ? (
                      <span className="flex items-center gap-1 text-xs text-green-600">
                        <Check className="w-3 h-3" /> Assigned
                      </span>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        disabled={assigningChar === char.name}
                        onClick={() => handleAssignVoice(char.name)}
                      >
                        {assigningChar === char.name
                          ? <Loader2 className="w-3 h-3 animate-spin" />
                          : "Assign"}
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VoiceModeSelector;
