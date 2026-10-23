import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "./api";
import VoiceInput, { toWav } from "./VoiceInput";

vi.mock("./api");

const track = { stop: vi.fn() };

class FakeRecorder {
  static last: FakeRecorder;
  state = "inactive";
  mimeType = "audio/webm";
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  constructor() { FakeRecorder.last = this; }
  start() { this.state = "recording"; }
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["sound"]) });
    this.onstop?.();
  }
}

// Two channels at 16 kHz: left 0.5, right -0.1, so the mono mix is 0.2.
class FakeOfflineContext {
  async decodeAudioData() {
    return { numberOfChannels: 2, length: 3, getChannelData: (i: number) => new Float32Array(3).fill(i ? -0.1 : 0.5) };
  }
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal("MediaRecorder", FakeRecorder);
  vi.stubGlobal("OfflineAudioContext", FakeOfflineContext);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [track] }) },
  });
  vi.mocked(api.transcribeSpeech).mockResolvedValue({ text: "Passport renew pannanum", language: "ta" });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("voice input", () => {
  it("records, converts to 16 kHz mono WAV, transcribes and hands over the editable text", async () => {
    const onTranscript = vi.fn();
    render(<VoiceInput language="ta" disabled={false} onTranscript={onTranscript} />);
    fireEvent.click(screen.getByRole("button", { name: "Speak your question" }));
    expect(await screen.findByText(/Recording… 0s \/ 30s/)).toBeTruthy();

    const stop = screen.getByRole("button", { name: "Stop and transcribe" });
    fireEvent.click(stop);
    fireEvent.click(stop); // a double click sends one recording

    await waitFor(() => expect(onTranscript).toHaveBeenCalledWith("Passport renew pannanum"));
    expect(api.transcribeSpeech).toHaveBeenCalledTimes(1);
    const [wav, language] = vi.mocked(api.transcribeSpeech).mock.calls[0];
    expect(language).toBe("ta");
    expect(wav.type).toBe("audio/wav");
    expect(track.stop).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Speak your question" })).toBeTruthy();
  });

  it("cancel discards the recording and releases the microphone", async () => {
    const onTranscript = vi.fn();
    render(<VoiceInput language="en" disabled={false} onTranscript={onTranscript} />);
    fireEvent.click(screen.getByRole("button", { name: "Speak your question" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));

    expect(track.stop).toHaveBeenCalled();
    expect(api.transcribeSpeech).not.toHaveBeenCalled();
    expect(onTranscript).not.toHaveBeenCalled();
  });

  it("stops by itself at 30 seconds", async () => {
    vi.useFakeTimers();
    try {
      render(<VoiceInput language="ta" disabled={false} onTranscript={vi.fn()} />);
      await act(async () => fireEvent.click(screen.getByRole("button", { name: "Speak your question" })));
      await act(async () => vi.advanceTimersByTime(30_500));
      expect(FakeRecorder.last.state).toBe("inactive");
      expect(api.transcribeSpeech).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("explains blocked microphones, failed transcriptions and unsupported browsers", async () => {
    vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValueOnce(new DOMException("denied", "NotAllowedError"));
    vi.mocked(api.transcribeSpeech).mockRejectedValueOnce(new Error("Voice input is not set up on this server. Type your question instead."));
    render(<VoiceInput language="ta" disabled={false} onTranscript={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Speak your question" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/Microphone access was blocked/);

    fireEvent.click(screen.getByRole("button", { name: "Speak your question" }));
    fireEvent.click(await screen.findByRole("button", { name: "Stop and transcribe" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/not set up on this server/);

    cleanup();
    vi.stubGlobal("MediaRecorder", undefined);
    render(<VoiceInput language="ta" disabled={false} onTranscript={vi.fn()} />);
    expect(screen.getByText(/not supported in this browser/)).toBeTruthy();
  });

  it("waits for microphone permission without opening a second microphone", async () => {
    let allow: (stream: { getTracks: () => typeof track[] }) => void = () => undefined;
    vi.mocked(navigator.mediaDevices.getUserMedia).mockReturnValueOnce(new Promise((resolve) => { allow = resolve; }) as never);
    render(<VoiceInput language="ta" disabled={false} onTranscript={vi.fn()} />);
    const speak = screen.getByRole("button", { name: "Speak your question" }) as HTMLButtonElement;
    fireEvent.click(speak);
    fireEvent.click(speak);

    expect(speak.disabled).toBe(true);
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1);
    await act(async () => allow({ getTracks: () => [track] }));
    expect(screen.getByRole("button", { name: "Stop and transcribe" })).toBeTruthy();
  });

  it("clears an old voice error when the next request starts", async () => {
    vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValueOnce(new DOMException("denied", "NotAllowedError"));
    const { rerender } = render(<VoiceInput language="ta" disabled={false} onTranscript={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Speak your question" }));
    expect(await screen.findByRole("alert")).toBeTruthy();

    rerender(<VoiceInput language="ta" disabled onTranscript={vi.fn()} />);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("is disabled while another request is running", () => {
    render(<VoiceInput language="ta" disabled onTranscript={vi.fn()} />);
    expect((screen.getByRole("button", { name: "Speak your question" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("toWav", () => {
  it("writes a 16 kHz mono 16-bit PCM WAV mixed down from all channels", async () => {
    const view = new DataView(await (await toWav(new Blob(["x"]))).arrayBuffer());
    const text = (offset: number, length: number) =>
      String.fromCharCode(...Array.from({ length }, (_, i) => view.getUint8(offset + i)));

    expect([text(0, 4), text(8, 8), text(36, 4)]).toEqual(["RIFF", "WAVEfmt ", "data"]);
    expect([view.getUint16(20, true), view.getUint16(22, true), view.getUint32(24, true), view.getUint16(34, true)])
      .toEqual([1, 1, 16000, 16]);
    expect([view.getUint32(40, true), view.byteLength]).toEqual([6, 50]);
    expect(view.getInt16(44, true)).toBe(Math.trunc(0.2 * 0x7fff));
  });
});
