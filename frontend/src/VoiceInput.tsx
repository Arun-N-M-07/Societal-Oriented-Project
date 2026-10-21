import { useEffect, useRef, useState } from "react";

import { transcribeSpeech, type Language } from "./api";


const MAX_SECONDS = 30; // the backend and the speech model accept up to 30 s
const RATE = 16000;

// The browser records in its own format (webm/ogg/mp4); the server accepts only
// 16 kHz mono 16-bit WAV, so decode, resample, mix down and encode it here.
export async function toWav(recording: Blob): Promise<Blob> {
  const decoded = await new OfflineAudioContext(1, 1, RATE).decodeAudioData(await recording.arrayBuffer());
  const channels = Array.from({ length: decoded.numberOfChannels }, (_, i) => decoded.getChannelData(i));
  const view = new DataView(new ArrayBuffer(44 + decoded.length * 2));
  const text = (offset: number, value: string) => [...value].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  text(0, "RIFF");
  view.setUint32(4, 36 + decoded.length * 2, true);
  text(8, "WAVEfmt ");
  view.setUint32(16, 16, true); // PCM header size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, RATE, true);
  view.setUint32(28, RATE * 2, true); // bytes per second
  view.setUint16(32, 2, true); // bytes per frame
  view.setUint16(34, 16, true); // bits per sample
  text(36, "data");
  view.setUint32(40, decoded.length * 2, true);
  for (let i = 0; i < decoded.length; i++) {
    const sample = channels.reduce((sum, channel) => sum + channel[i], 0) / channels.length;
    view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, sample)) * 0x7fff, true);
  }
  return new Blob([view], { type: "audio/wav" });
}

const MIC_ERRORS: Record<string, string> = {
  NotAllowedError: "Microphone access was blocked. Allow it in your browser, or type your question.",
  NotFoundError: "No microphone was found. Type your question instead.",
};

type Props = { language: Language; disabled: boolean; onTranscript: (text: string) => void };

// Record a short question; the transcript is put in the question box to check and edit.
export default function VoiceInput({ language, disabled, onTranscript }: Props) {
  const [state, setState] = useState<"idle" | "recording" | "transcribing">("idle");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const cancelled = useRef(false);
  const timer = useRef<number | undefined>(undefined);

  const stop = (cancel: boolean) => {
    cancelled.current = cancel;
    if (recorder.current?.state === "recording") recorder.current.stop();
  };
  // Leaving the page while recording releases the microphone and discards the audio.
  useEffect(() => () => {
    window.clearInterval(timer.current);
    stop(true);
  }, []);

  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    return <p className="field-help">Voice input is not supported in this browser. Type your question instead.</p>;
  }

  async function start() {
    setError(null);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (micError) {
      setError(MIC_ERRORS[(micError as DOMException).name] ?? "The microphone could not be started. Type your question instead.");
      return;
    }
    const chunks: Blob[] = [];
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (event) => chunks.push(event.data);
    rec.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      window.clearInterval(timer.current);
      recorder.current = null;
      if (cancelled.current) return setState("idle");
      setState("transcribing");
      try {
        const { text } = await transcribeSpeech(await toWav(new Blob(chunks, { type: rec.mimeType })), language);
        onTranscript(text);
      } catch (requestError) {
        setError(requestError instanceof Error && requestError.name !== "EncodingError"
          ? requestError.message : "The recording could not be read. Try again.");
      } finally {
        setState("idle");
      }
    };
    recorder.current = rec;
    cancelled.current = false;
    rec.start();
    setSeconds(0);
    setState("recording");
    const started = Date.now();
    timer.current = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - started) / 1000);
      setSeconds(elapsed);
      if (elapsed >= MAX_SECONDS) stop(false);
    }, 250);
  }

  return (
    <div className="voice-input">
      {state === "recording" ? (
        <>
          <button className="secondary-button" type="button" onClick={() => stop(false)}>Stop and transcribe</button>{" "}
          <button className="secondary-button" type="button" onClick={() => stop(true)}>Cancel</button>{" "}
          <span role="status">Recording… {seconds}s / {MAX_SECONDS}s</span>
        </>
      ) : (
        <button className="secondary-button" type="button" disabled={disabled || state === "transcribing"} onClick={() => void start()}>
          {state === "transcribing" ? "Transcribing…" : "Speak your question"}
        </button>
      )}
      {error && <p className="feedback error" role="alert">{error}</p>}
    </div>
  );
}
