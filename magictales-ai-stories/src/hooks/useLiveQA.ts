import { useCallback, useRef, useState, type RefObject } from "react";

/** Build WebSocket URL for Gemini Live Q&A (same host in dev via Vite proxy, or VITE_API_ORIGIN in prod). */
export function getLiveQaWebSocketUrl(storyId: string): string {
  const origin = import.meta.env.VITE_API_ORIGIN as string | undefined;
  if (origin?.trim()) {
    let u: URL;
    try {
      u = new URL(origin);
    } catch {
      u = new URL(origin, window.location.origin);
    }
    const wsProto = u.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProto}//${u.host}/ws/stories/${storyId}/live`;
  }
  const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProto}//${window.location.host}/ws/stories/${storyId}/live`;
}

const LIVE_MIC_SPEECH_RMS = 0.055;
const LIVE_BARGE_IN_COOLDOWN_MS = 120;
const LIVE_REPLY_END_GAP_MS = 480;

function downsampleTo16kInt16(float32: Float32Array, inRate: number): Int16Array {
  const ratio = inRate / 16000;
  const n = Math.floor(float32.length / ratio);
  const out = new Int16Array(n);
  for (let i = 0; i < n; i++) {
    const j = Math.floor(i * ratio);
    let s = Math.max(-1, Math.min(1, float32[j]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

export type LiveQaUiStatus = "idle" | "connecting" | "listening" | "replying" | "error" | "stopped";

export interface UseLiveQAOptions {
  storyId: string;
  audiobookRef: RefObject<HTMLAudioElement | null>;
  bgmRef: RefObject<HTMLAudioElement | null>;
}

/**
 * Browser mic → backend `/ws/stories/:id/live` → Gemini Live → speaker PCM.
 * Pauses audiobook/BGM while the model replies; resumes after playback.
 */
export function useLiveQA({ storyId, audiobookRef, bgmRef }: UseLiveQAOptions) {
  const [status, setStatus] = useState<LiveQaUiStatus>("idle");
  const [statusDetail, setStatusDetail] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const captureCtxRef = useRef<AudioContext | null>(null);
  const procRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const playCtxRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef(0);
  const heardReplyRef = useRef(false);
  const playSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const lastBargeInRef = useRef(0);
  const pausedAudiobookRef = useRef(false);
  const pausedBgmRef = useRef(false);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const innerResumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const expectCloseRef = useRef(false);

  const flushLiveModelAudio = useCallback(() => {
    const playCtx = playCtxRef.current;
    if (!playCtx) return;
    const now = performance.now();
    if (now - lastBargeInRef.current < LIVE_BARGE_IN_COOLDOWN_MS) return;
    lastBargeInRef.current = now;
    if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    if (innerResumeTimerRef.current) clearTimeout(innerResumeTimerRef.current);
    resumeTimerRef.current = null;
    innerResumeTimerRef.current = null;
    for (const s of playSourcesRef.current) {
      try {
        s.stop(0);
      } catch {
        /* ignore */
      }
    }
    playSourcesRef.current = [];
    nextPlayTimeRef.current = playCtx.currentTime;
  }, []);

  const maybePauseStoryForQA = useCallback(() => {
    const ap = audiobookRef.current;
    if (ap && !ap.paused) {
      ap.pause();
      pausedAudiobookRef.current = true;
    }
    const bgm = bgmRef.current;
    if (bgm && !bgm.paused) {
      bgm.pause();
      pausedBgmRef.current = true;
    }
  }, [audiobookRef, bgmRef]);

  const scheduleResumeAudiobookAfterLiveReply = useCallback(() => {
    if (!pausedAudiobookRef.current) return;
    if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    if (innerResumeTimerRef.current) clearTimeout(innerResumeTimerRef.current);
    resumeTimerRef.current = setTimeout(() => {
      resumeTimerRef.current = null;
      if (!pausedAudiobookRef.current || !playCtxRef.current) return;
      const playCtx = playCtxRef.current;
      const msLeft = Math.max(0, (nextPlayTimeRef.current - playCtx.currentTime) * 1000) + 60;
      innerResumeTimerRef.current = setTimeout(() => {
        innerResumeTimerRef.current = null;
        if (!pausedAudiobookRef.current) return;
        const ap = audiobookRef.current;
        if (ap?.paused) void ap.play().catch(() => {});
        if (pausedBgmRef.current) {
          const bgm = bgmRef.current;
          if (bgm?.src) void bgm.play().catch(() => {});
          pausedBgmRef.current = false;
        }
        pausedAudiobookRef.current = false;
        setStatus("listening");
        setStatusDetail(null);
      }, msLeft);
    }, LIVE_REPLY_END_GAP_MS);
  }, [audiobookRef, bgmRef]);

  const maybeBargeInFromMic = useCallback(
    (inputFloat32: Float32Array) => {
      let sum = 0;
      for (let i = 0; i < inputFloat32.length; i++) sum += inputFloat32[i] * inputFloat32[i];
      const rms = Math.sqrt(sum / inputFloat32.length);
      if (rms < LIVE_MIC_SPEECH_RMS) return;
      flushLiveModelAudio();
      maybePauseStoryForQA();
    },
    [flushLiveModelAudio, maybePauseStoryForQA]
  );

  const teardownLiveMediaOnly = useCallback(() => {
    if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    if (innerResumeTimerRef.current) clearTimeout(innerResumeTimerRef.current);
    resumeTimerRef.current = null;
    innerResumeTimerRef.current = null;
    if (procRef.current) {
      try {
        procRef.current.disconnect();
      } catch {
        /* ignore */
      }
      procRef.current = null;
    }
    if (captureCtxRef.current) {
      try {
        void captureCtxRef.current.close();
      } catch {
        /* ignore */
      }
      captureCtxRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (playCtxRef.current) {
      for (const s of playSourcesRef.current) {
        try {
          s.stop(0);
        } catch {
          /* ignore */
        }
      }
      playSourcesRef.current = [];
      try {
        void playCtxRef.current.close();
      } catch {
        /* ignore */
      }
      playCtxRef.current = null;
    }
    nextPlayTimeRef.current = 0;
  }, []);

  const stopLiveQA = useCallback(
    (silent: boolean) => {
      expectCloseRef.current = true;
      if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
      if (innerResumeTimerRef.current) clearTimeout(innerResumeTimerRef.current);
      resumeTimerRef.current = null;
      innerResumeTimerRef.current = null;
      teardownLiveMediaOnly();
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          /* ignore */
        }
        wsRef.current = null;
      }
      if (pausedAudiobookRef.current) {
        pausedAudiobookRef.current = false;
        const ap = audiobookRef.current;
        if (ap) void ap.play().catch(() => {});
      }
      if (pausedBgmRef.current) {
        const bgm = bgmRef.current;
        if (bgm?.src) void bgm.play().catch(() => {});
        pausedBgmRef.current = false;
      }
      if (!silent) {
        setStatus("stopped");
        setStatusDetail(null);
      } else {
        setStatus("idle");
        setStatusDetail(null);
      }
    },
    [audiobookRef, bgmRef, teardownLiveMediaOnly]
  );

  const startLiveQA = useCallback(() => {
    if (!storyId) return Promise.resolve();
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return Promise.resolve();

    heardReplyRef.current = false;
    setStatus("connecting");
    setStatusDetail(null);

    const ws = new WebSocket(getLiveQaWebSocketUrl(storyId));
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;
    expectCloseRef.current = false;

    return new Promise<void>((resolve, reject) => {
      let settled = false;
      const ok = () => {
        if (!settled) {
          settled = true;
          resolve();
        }
      };
      const fail = (e: unknown) => {
        if (!settled) {
          settled = true;
          reject(e instanceof Error ? e : new Error(String(e)));
        }
      };

      ws.onopen = async () => {
        try {
          streamRef.current = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
          });
          captureCtxRef.current = new AudioContext();
          const cap = captureCtxRef.current;
          if (cap.state === "suspended") await cap.resume();
          const source = cap.createMediaStreamSource(streamRef.current);
          const proc = cap.createScriptProcessor(4096, 1, 1);
          procRef.current = proc;
          proc.onaudioprocess = (e) => {
            if (ws.readyState !== WebSocket.OPEN) return;
            const input = e.inputBuffer.getChannelData(0);
            maybeBargeInFromMic(input);
            const pcm = downsampleTo16kInt16(input, cap.sampleRate);
            ws.send(pcm.buffer);
          };
          const gain = cap.createGain();
          gain.gain.value = 0;
          source.connect(proc);
          proc.connect(gain);
          gain.connect(cap.destination);
          try {
            playCtxRef.current = new AudioContext({ sampleRate: 24000 });
          } catch {
            playCtxRef.current = new AudioContext();
          }
          const playCtx = playCtxRef.current;
          if (playCtx!.state === "suspended") await playCtx!.resume();
          nextPlayTimeRef.current = playCtx!.currentTime;
          setStatus("listening");
          ok();
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          setStatus("error");
          setStatusDetail(`Mic error: ${msg}`);
          expectCloseRef.current = true;
          try {
            ws.close();
          } catch {
            /* ignore */
          }
          fail(err);
        }
      };

      ws.onmessage = (ev) => {
        const playCtx = playCtxRef.current;
        if (!(ev.data instanceof ArrayBuffer) || !playCtx) return;
        if (!heardReplyRef.current) {
          heardReplyRef.current = true;
          setStatus("replying");
        }
        const pcm = new Int16Array(ev.data);
        const rate = playCtx.sampleRate;
        const buf = playCtx.createBuffer(1, pcm.length, rate);
        const ch = buf.getChannelData(0);
        for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 32768;
        const src = playCtx.createBufferSource();
        src.buffer = buf;
        src.connect(playCtx.destination);
        playSourcesRef.current.push(src);
        src.onended = () => {
          const i = playSourcesRef.current.indexOf(src);
          if (i >= 0) playSourcesRef.current.splice(i, 1);
        };
        const start = Math.max(playCtx.currentTime, nextPlayTimeRef.current);
        src.start(start);
        nextPlayTimeRef.current = start + buf.duration;
        scheduleResumeAudiobookAfterLiveReply();
      };

      ws.onerror = () => {
        setStatus("error");
        setStatusDetail("WebSocket error.");
        fail(new Error("WebSocket error"));
      };

      ws.onclose = () => {
        const wasOpen = wsRef.current === ws;
        wsRef.current = null;
        if (wasOpen && !expectCloseRef.current) {
          setStatus("error");
          setStatusDetail("Live Q&A disconnected.");
        }
        expectCloseRef.current = false;
        teardownLiveMediaOnly();
      };
    });
  }, [storyId, maybeBargeInFromMic, scheduleResumeAudiobookAfterLiveReply, teardownLiveMediaOnly]);

  return {
    liveQaStatus: status,
    liveQaDetail: statusDetail,
    startLiveQA,
    stopLiveQA,
  };
}
