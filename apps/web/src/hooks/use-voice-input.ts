"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionResultEvent = {
  resultIndex: number;
  results: SpeechRecognitionResultList;
};

const WHISPER_FALLBACK_ERRORS = new Set(["network", "service-not-allowed", "no-speech"]);
const USE_BROWSER_SPEECH =
  process.env.NEXT_PUBLIC_VOICE_USE_BROWSER === "true";

function getSpeechRecognition(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function canRecordAudio(): boolean {
  return (
    typeof window !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    typeof MediaRecorder !== "undefined"
  );
}

function mapSpeechError(code: string): string | null {
  switch (code) {
    case "aborted":
      return null;
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone blocked. Allow mic access for this site in browser settings.";
    case "audio-capture":
      return "No microphone found or mic is in use by another app.";
    case "no-speech":
      return "No speech detected. Tap mic and speak clearly.";
    case "network":
      return "Browser speech unavailable. Using server transcription.";
    case "language-not-supported":
      return "Voice language not supported in this browser.";
    default:
      return `Voice input failed (${code}).`;
  }
}

async function ensureMicrophoneAccess(): Promise<string | null> {
  if (!navigator.mediaDevices?.getUserMedia) return null;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
    return null;
  } catch (err) {
    const name = err instanceof DOMException ? err.name : "unknown";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      return "Microphone blocked. Allow mic access for this site in browser settings.";
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError") {
      return "No microphone found.";
    }
    return "Could not access microphone.";
  }
}

async function transcribeBlob(blob: Blob): Promise<string> {
  const form = new FormData();
  form.append("file", blob, "voice.webm");
  const response = await fetch("/api/transcribe", { method: "POST", body: form });
  const payload = (await response.json()) as { text?: string; error?: string };
  if (!response.ok) {
    throw new Error(payload.error ?? "Transcription failed");
  }
  return (payload.text ?? "").trim();
}

export function useVoiceInput(onTranscript: (text: string, isFinal: boolean) => void) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recordTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const whisperActiveRef = useRef(false);
  const onTranscriptRef = useRef(onTranscript);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    const hasSpeech = Boolean(getSpeechRecognition());
    const hasRecord = canRecordAudio();
    setSupported(hasSpeech || hasRecord);
  }, []);

  const cleanupStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const stopRecording = useCallback(() => {
    if (recordTimerRef.current) {
      clearTimeout(recordTimerRef.current);
      recordTimerRef.current = null;
    }
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      whisperActiveRef.current = false;
      setRecording(false);
      setListening(false);
      cleanupStream();
      return;
    }
    recorder.stop();
  }, [cleanupStream]);

  const startWhisperFallback = useCallback(async () => {
    if (!canRecordAudio()) {
      setError("Voice recording not supported in this browser.");
      return;
    }

    whisperActiveRef.current = true;
    setError(null);
    setListening(true);
    setRecording(true);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        cleanupStream();
        whisperActiveRef.current = false;
        setRecording(false);
        setListening(false);
        recorderRef.current = null;

        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        chunksRef.current = [];

        if (blob.size < 1000) {
          setError("No audio captured. Tap mic and speak.");
          return;
        }

        try {
          const text = await transcribeBlob(blob);
          if (text) {
            onTranscriptRef.current(text, true);
            setError(null);
          } else {
            setError("No speech detected. Try again.");
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : "Transcription failed");
        }
      };

      recorder.start(250);
      recordTimerRef.current = setTimeout(() => {
        stopRecording();
      }, 12000);
    } catch (err) {
      whisperActiveRef.current = false;
      setRecording(false);
      setListening(false);
      cleanupStream();
      const name = err instanceof DOMException ? err.name : "unknown";
      setError(
        name === "NotAllowedError"
          ? "Microphone blocked. Allow mic access for this site."
          : "Could not start recording.",
      );
    }
  }, [cleanupStream, stopRecording]);

  const stopBrowserSpeech = useCallback(() => {
    try {
      recognitionRef.current?.abort();
    } catch {
      recognitionRef.current?.stop();
    }
    recognitionRef.current = null;
    if (!whisperActiveRef.current) setListening(false);
  }, []);

  const startBrowserSpeech = useCallback(async () => {
    const Ctor = getSpeechRecognition();
    if (!Ctor) {
      await startWhisperFallback();
      return;
    }

    setError(null);

    const micError = await ensureMicrophoneAccess();
    if (micError) {
      setError(micError);
      return;
    }

    stopBrowserSpeech();

    const recognition = new Ctor();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }
      const isFinal = event.results[event.results.length - 1]?.isFinal ?? false;
      onTranscriptRef.current(transcript.trim(), isFinal);
      if (isFinal) setError(null);
    };

    recognition.onerror = (event) => {
      setListening(false);
      if (WHISPER_FALLBACK_ERRORS.has(event.error)) {
        void startWhisperFallback();
        return;
      }
      const message = mapSpeechError(event.error);
      if (message) setError(message);
    };

    recognition.onend = () => {
      if (!whisperActiveRef.current) setListening(false);
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
      setListening(true);
    } catch {
      await startWhisperFallback();
    }
  }, [startWhisperFallback, stopBrowserSpeech]);

  const start = useCallback(async () => {
    if (USE_BROWSER_SPEECH && getSpeechRecognition()) {
      await startBrowserSpeech();
    } else {
      await startWhisperFallback();
    }
  }, [startBrowserSpeech, startWhisperFallback]);

  const stop = useCallback(() => {
    if (recording || whisperActiveRef.current) {
      stopRecording();
      return;
    }
    stopBrowserSpeech();
  }, [recording, stopBrowserSpeech, stopRecording]);

  const toggle = useCallback(() => {
    if (listening || recording) {
      stop();
    } else {
      void start();
    }
  }, [listening, recording, start, stop]);

  return { supported, listening: listening || recording, recording, error, toggle, stop };
}
