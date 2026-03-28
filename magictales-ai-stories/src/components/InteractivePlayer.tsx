import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Play, Pause, SkipForward, SkipBack, Mic, MicOff, Loader2, Radio } from "lucide-react";
import type { ProcessedStory } from "@/types/story";
import { useLiveQA } from "@/hooks/useLiveQA";

interface InteractivePlayerProps {
  story: ProcessedStory;
  voiceMode: "ai" | "record";
  voiceSample: string | null;
  onStop: () => void;
}

const InteractivePlayer = ({ story, voiceMode, voiceSample, onStop }: InteractivePlayerProps) => {
  const navigate = useNavigate();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isFinished, setIsFinished] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [pulseActive, setPulseActive] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [recordedAudios, setRecordedAudios] = useState<Record<number, string>>({});
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const audioEl = useRef<HTMLAudioElement | null>(null);
  const bgmEl = useRef<HTMLAudioElement | null>(null);
  const liveQaStartedRef = useRef(false);
  const blobCache = useRef<Record<number, string>>({});
  const currentIndexRef = useRef(0);
  const stoppedRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  const { liveQaStatus, liveQaDetail, startLiveQA, stopLiveQA } = useLiveQA({
    storyId: story.story_id,
    audiobookRef: audioEl,
    bgmRef: bgmEl,
  });

  const totalSegments = story.segments.length;
  const safeIndex = Math.max(0, Math.min(currentSegmentIndex, totalSegments - 1));
  const progress = totalSegments > 0 ? Math.round(((safeIndex + 1) / totalSegments) * 100) : 0;
  const currentSegment = story.segments[safeIndex];
  const estimatedTotalSeconds = totalSegments * 4;
  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  // Fetch segment audio as blob URL (with cache)
  const fetchSegment = useCallback(async (index: number): Promise<string> => {
    if (blobCache.current[index]) return blobCache.current[index];
    const res = await fetch(`/api/stories/${story.story_id}/audio/${index}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    blobCache.current[index] = url;
    return url;
  }, [story.story_id]);

  const setBgmEmotion = useCallback((emotion: string) => {
    if (!bgmEl.current) {
      bgmEl.current = new Audio();
      bgmEl.current.loop = true;
      bgmEl.current.volume = 0.2;
    }
    const bgmUrl = `/api/stories/${story.story_id}/music/${emotion}`;
    if (bgmEl.current.src.endsWith(bgmUrl)) return;
    bgmEl.current.src = bgmUrl;
    bgmEl.current.play().catch(() => {});
  }, [story.story_id]);

  const playSegment = useCallback(async (index: number) => {
    if (stoppedRef.current) return;
    if (index >= totalSegments) {
      liveQaStartedRef.current = false;
      stopLiveQA(true);
      setIsPlaying(false);
      setIsFinished(true);
      setIsLoadingAudio(false);
      bgmEl.current?.pause();
      return;
    }

    currentIndexRef.current = index;
    setCurrentSegmentIndex(index);
    setIsLoadingAudio(true);
    setAudioError(null);

    try {
      const blobUrl = await fetchSegment(index);
      if (stoppedRef.current) return;

      if (!audioEl.current) audioEl.current = new Audio();
      const player = audioEl.current;
      player.src = blobUrl;
      player.onended = () => {
        if (!stoppedRef.current) playSegment(currentIndexRef.current + 1);
      };
      await player.play();
      setIsLoadingAudio(false);

      // BGM
      const seg = story.segments[index];
      if (seg) setBgmEmotion(seg.emotion);

      // Gemini Live Q&A (AI voice mode): mic → backend WebSocket → spoken reply
      if (voiceMode === "ai" && !liveQaStartedRef.current) {
        liveQaStartedRef.current = true;
        void startLiveQA().catch((e) => {
          liveQaStartedRef.current = false;
          console.error("Live Q&A:", e);
        });
      }

      // Pre-fetch next
      if (index + 1 < totalSegments) {
        fetchSegment(index + 1).catch(() => {});
      }
    } catch (err: unknown) {
      if (stoppedRef.current) return;
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`Segment ${index} error:`, msg);
      setAudioError(`Segment ${index + 1} failed — skipping`);
      setIsLoadingAudio(false);
      setTimeout(() => setAudioError(null), 3000);
      playSegment(index + 1);
    }
  }, [
    story.story_id,
    story.segments,
    totalSegments,
    fetchSegment,
    setBgmEmotion,
    voiceMode,
    startLiveQA,
    stopLiveQA,
  ]);

  // Timer
  useEffect(() => {
    if (isPlaying && !isPaused) {
      timerRef.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isPlaying, isPaused]);

  useEffect(() => {
    setPulseActive(isPlaying && !isPaused && !isLoadingAudio);
  }, [isPlaying, isPaused, isLoadingAudio]);

  useEffect(() => {
    if (isFinished) navigate("/study-card", { state: { story } });
  }, [isFinished, navigate, story]);

  // Cleanup on unmount
  useEffect(() => {
    stoppedRef.current = false;
    return () => {
      stoppedRef.current = true;
      liveQaStartedRef.current = false;
      stopLiveQA(true);
      audioEl.current?.pause();
      bgmEl.current?.pause();
      clearInterval(timerRef.current);
      Object.values(blobCache.current).forEach(URL.revokeObjectURL);
    };
  }, [stopLiveQA]);

  const handlePlay = useCallback(() => {
    liveQaStartedRef.current = false;
    stopLiveQA(true);
    setIsPlaying(true);
    setIsPaused(false);
    if (voiceMode === "ai") playSegment(currentIndexRef.current);
  }, [voiceMode, playSegment, stopLiveQA]);

  const handlePause = useCallback(() => {
    setIsPaused(true);
    audioEl.current?.pause();
    bgmEl.current?.pause();
  }, []);

  const handleResume = useCallback(() => {
    setIsPaused(false);
    audioEl.current?.play().catch(console.error);
    bgmEl.current?.play().catch(() => {});
  }, []);

  const handleStop = useCallback(() => {
    stoppedRef.current = true;
    liveQaStartedRef.current = false;
    stopLiveQA(true);
    audioEl.current?.pause();
    bgmEl.current?.pause();
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    clearInterval(timerRef.current);
    onStop();
  }, [onStop, stopLiveQA]);

  const handleSkipForward = useCallback(() => {
    const next = Math.min(currentIndexRef.current + 1, totalSegments - 1);
    if (voiceMode === "ai") {
      audioEl.current?.pause();
      playSegment(next);
    } else {
      setCurrentSegmentIndex(next);
    }
  }, [totalSegments, voiceMode, playSegment]);

  const handleSkipBack = useCallback(() => {
    const prev = Math.max(currentIndexRef.current - 1, 0);
    if (voiceMode === "ai") {
      audioEl.current?.pause();
      playSegment(prev);
    } else {
      setCurrentSegmentIndex(prev);
    }
  }, [voiceMode, playSegment]);

  const handleReplay = useCallback(() => {
    liveQaStartedRef.current = false;
    stopLiveQA(true);
    stoppedRef.current = false;
    setIsFinished(false);
    setIsPlaying(true);
    setElapsedSeconds(0);
    if (voiceMode === "ai") playSegment(0);
  }, [voiceMode, playSegment, stopLiveQA]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setRecordedAudios((p) => ({ ...p, [safeIndex]: URL.createObjectURL(blob) }));
        stream.getTracks().forEach((t) => t.stop());
      };
      mr.start();
      setIsRecording(true);
    } catch { console.error("Mic denied"); }
  }, [safeIndex]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setIsRecording(false);
  }, []);

  return (
    <div className="space-y-6 animate-fade-up">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[hsl(260,50%,15%)] via-[hsl(280,40%,20%)] to-[hsl(230,50%,15%)] p-8 shadow-2xl">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div
            className={`w-64 h-64 rounded-full transition-all duration-1000 ${pulseActive ? "animate-pulse scale-110" : "scale-100"}`}
            style={{ background: "radial-gradient(circle, hsla(280,80%,60%,0.3) 0%, hsla(220,80%,60%,0.15) 50%, transparent 70%)", filter: "blur(30px)" }}
          />
        </div>

        <div className="relative z-10 flex flex-col items-center text-center">
          <h2 className="font-display font-extrabold text-xl text-white mb-1">{story.title}</h2>
          <p className="text-sm text-white/50 font-body mb-6">{totalSegments} segments</p>

          {/* Icon */}
          <div className="relative mb-6">
            <div
              className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-700 ${pulseActive ? "shadow-[0_0_60px_hsla(260,80%,60%,0.5)]" : ""}`}
              style={{ background: "radial-gradient(circle, hsla(260,50%,25%,0.8) 0%, hsla(260,50%,15%,0.6) 100%)", border: "2px solid hsla(260,60%,60%,0.3)" }}
            >
              {isLoadingAudio
                ? <Loader2 className="w-10 h-10 text-white/70 animate-spin" />
                : <Mic className={`w-10 h-10 text-white/90 transition-transform duration-500 ${pulseActive ? "scale-110" : "scale-100"}`} />
              }
            </div>
            {pulseActive && (
              <div className="absolute inset-0 rounded-full animate-ping" style={{ border: "2px solid hsla(260,60%,60%,0.2)", animationDuration: "2s" }} />
            )}
          </div>

          {isLoadingAudio && <p className="text-xs text-white/50 font-body mb-4">Generating audio…</p>}
          {audioError && <p className="text-xs text-red-400 font-body mb-4">{audioError}</p>}

          {voiceMode === "ai" && isPlaying && !isFinished && liveQaStatus !== "idle" && (
            <div className="w-full max-w-md mb-4 rounded-xl border border-violet-400/30 bg-violet-950/40 px-3 py-2 text-left">
              <div className="flex items-center gap-2 text-xs font-medium text-violet-200">
                <Radio className="w-3.5 h-3.5 shrink-0" />
                Live Q&amp;A (Gemini + mic)
              </div>
              <p className="text-[11px] text-violet-200/80 mt-1 font-body">
                {liveQaDetail ||
                  (liveQaStatus === "connecting" && "Connecting…") ||
                  (liveQaStatus === "listening" && "Listening — ask about the story.") ||
                  (liveQaStatus === "replying" && "Playing reply…") ||
                  (liveQaStatus === "stopped" && "Stopped.") ||
                  (liveQaStatus === "error" && "Something went wrong.") ||
                  ""}
              </p>
            </div>
          )}

          {/* Segment text */}
          {currentSegment && (
            <div className="max-w-md mb-6">
              <p className="text-xs text-white/40 font-body mb-1.5">
                {currentSegment.speaker.toLowerCase() === "narrator"
                  ? "📖 Narrator"
                  : `${story.characters.find(c => c.name.toLowerCase() === currentSegment.speaker.toLowerCase())?.emoji || "🗣️"} ${currentSegment.speaker}`}
                {" · "}
                <span className="capitalize">{currentSegment.emotion}</span>
              </p>
              <p className="font-body text-white/80 text-sm leading-relaxed italic">
                "{currentSegment.text}"
              </p>
            </div>
          )}

          {/* Record controls */}
          {voiceMode === "record" && isPlaying && !isFinished && (
            <div className="flex items-center gap-3 mb-4">
              {isRecording ? (
                <Button variant="destructive" size="sm" onClick={stopRecording} className="bg-red-500/80 hover:bg-red-500">
                  <MicOff className="w-4 h-4 mr-1" />Stop Recording
                </Button>
              ) : (
                <Button size="sm" onClick={startRecording} className="bg-white/10 hover:bg-white/20 text-white border-white/20">
                  <Mic className="w-4 h-4 mr-1" />Read Aloud
                </Button>
              )}
              {recordedAudios[safeIndex] && <audio src={recordedAudios[safeIndex]} controls className="h-8" />}
            </div>
          )}

          {/* Progress */}
          <div className="w-full max-w-sm mb-4">
            <div className="w-full bg-white/10 rounded-full h-1.5 mb-2">
              <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${progress}%`, background: "linear-gradient(90deg, hsl(260,60%,60%), hsl(200,80%,55%))" }} />
            </div>
            <div className="flex justify-between text-xs text-white/40 font-body">
              <span>{formatTime(elapsedSeconds)}</span>
              <span>Segment {safeIndex + 1} / {totalSegments}</span>
              <span>~{formatTime(estimatedTotalSeconds)}</span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3">
            <button onClick={handleSkipBack} className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors">
              <SkipBack className="w-4 h-4 text-white/70" />
            </button>

            {isFinished ? (
              <button onClick={handleReplay} className="w-14 h-14 rounded-full flex items-center justify-center transition-all hover:scale-105" style={{ background: "linear-gradient(135deg, hsl(260,60%,55%), hsl(200,80%,55%))" }}>
                <Play className="w-6 h-6 text-white ml-0.5" />
              </button>
            ) : !isPlaying ? (
              <button onClick={handlePlay} className="w-14 h-14 rounded-full flex items-center justify-center transition-all hover:scale-105" style={{ background: "linear-gradient(135deg, hsl(260,60%,55%), hsl(200,80%,55%))" }}>
                <Play className="w-6 h-6 text-white ml-0.5" />
              </button>
            ) : isPaused ? (
              <button onClick={handleResume} className="w-14 h-14 rounded-full flex items-center justify-center transition-all hover:scale-105" style={{ background: "linear-gradient(135deg, hsl(260,60%,55%), hsl(200,80%,55%))" }}>
                <Play className="w-6 h-6 text-white ml-0.5" />
              </button>
            ) : (
              <button onClick={handlePause} className="w-14 h-14 rounded-full flex items-center justify-center transition-all hover:scale-105" style={{ background: "linear-gradient(135deg, hsl(260,60%,55%), hsl(200,80%,55%))" }}>
                <Pause className="w-6 h-6 text-white" />
              </button>
            )}

            <button onClick={handleSkipForward} className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors">
              <SkipForward className="w-4 h-4 text-white/70" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InteractivePlayer;
