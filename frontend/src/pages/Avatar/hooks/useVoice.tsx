import { Message } from "@/interfaces/interfaces";
import { useState, useRef, useCallback, useEffect } from "react";

type AnalyzerData = {
  analyzer: AnalyserNode;
  bufferLength: number;
  dataArray: Uint8Array;
};

type UseVoiceAssistantProps = {
  setMsg: React.Dispatch<React.SetStateAction<Message[]>>;
};

export function useVoiceAssistant({ setMsg }: UseVoiceAssistantProps) {
  const [status, setStatus] = useState<string>("idle");
  const [analyzerData, setAnalyzerData] = useState<AnalyzerData | null>(null);

  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const queueTimeRef = useRef<number | undefined>(undefined);
  const assistantSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const partialBufRef = useRef<string>("");

  const int16ToFloat32 = (int16: Int16Array): Float32Array => {
    const f32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      const int = int16[i];
      f32[i] = int < 0 ? int / 0x8000 : int / 0x7fff;
    }
    return f32;
  };

  const playChunk = (base64: string) => {
    const bin = atob(base64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const int16 = new Int16Array(bytes.buffer);
    const f32 = int16ToFloat32(int16);

    const ctx =
      audioCtxRef.current ||
      (audioCtxRef.current = new AudioContext({ sampleRate: 24000 }));

    if (!analyserRef.current) {
      analyserRef.current = ctx.createAnalyser();
      analyserRef.current.fftSize = 2048;
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      setAnalyzerData({
        analyzer: analyserRef.current,
        bufferLength,
        dataArray,
      });
    }

    if (queueTimeRef.current === undefined) {
      queueTimeRef.current = ctx.currentTime;
    }

    const buf = ctx.createBuffer(1, f32.length, 24000);
    buf.copyToChannel(f32, 0);

    const src = ctx.createBufferSource();
    src.buffer = buf;

    src.connect(analyserRef.current!);
    analyserRef.current!.connect(ctx.destination);

    const startAt = Math.max(queueTimeRef.current, ctx.currentTime + 0.05);
    src.start(startAt);
    queueTimeRef.current = startAt + buf.duration;

    assistantSourcesRef.current.push(src);
    src.onended = () => {
      assistantSourcesRef.current = assistantSourcesRef.current.filter(
        (s) => s !== src
      );
      if (assistantSourcesRef.current.length === 0) {
        setStatus("Escuchando");
      }
    };
  };

  const start = useCallback(async () => {
    if (status !== "idle") return;

    setStatus("Conectando");

    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext({ sampleRate: 24000 });
    }
    await audioCtxRef.current.audioWorklet.addModule("/recorder-worklet.js");

    mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({
      audio: true,
    });
    const source = audioCtxRef.current.createMediaStreamSource(
      mediaStreamRef.current
    );
    const node = new AudioWorkletNode(
      audioCtxRef.current,
      "recorder-processor"
    );
    source.connect(node);
    node.connect(audioCtxRef.current.destination);

    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    wsRef.current = new WebSocket(`${proto}//${location.host}/realtime`);

    wsRef.current.onopen = async () => {
      wsRef.current?.send(
        JSON.stringify({ type: "session.update", session: {} })
      );
      await playWelcomeAudio();
    };

    wsRef.current.onmessage = (ev: MessageEvent) => {
      const m = JSON.parse(ev.data);
      switch (m.type) {
        case "assistant.audio":
          setStatus("Hablando");
          playChunk(m.audio);
          break;
        case "transcript.delta":
          partialBufRef.current += m.text;
          break;
        case "transcript.final":
          partialBufRef.current = "";
          if (m.role === "assistant") setStatus("Hablando");
          if (m.role == "assistant" || (m.role == "user" && m.text)) {
            setMsg((prev) => [...prev, { role: m.role, value: m.text }]);
          }
          break;
        case "speech_started":
          setStatus("Escuchando");
          stopAssistantAudio();
          break;
        case "tool_result":
          break;
      }
    };

    wsRef.current.onclose = () => stop();

    node.port.onmessage = (ev: MessageEvent) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      const int16 = new Int16Array(ev.data as ArrayBuffer);
      const bytes = new Uint8Array(int16.buffer);
      let bin = "";
      bytes.forEach((b) => (bin += String.fromCharCode(b)));
      const base64 = btoa(bin);
      wsRef.current.send(
        JSON.stringify({ type: "input_audio_buffer.append", audio: base64 })
      );
    };
  }, [status]);

  const stopAssistantAudio = () => {
    assistantSourcesRef.current.forEach((s) => {
      try {
        s.stop();
      } catch {
        /* ignore */
      }
    });
    assistantSourcesRef.current = [];
    if (audioCtxRef.current) {
      queueTimeRef.current = audioCtxRef.current.currentTime;
    }
  };

  const stop = useCallback(() => {
    if (status === "idle") return;
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    stopAssistantAudio();
    partialBufRef.current = "";
    queueTimeRef.current = undefined;
    assistantSourcesRef.current = [];
    setStatus("idle");
  }, [status]);

  async function playWelcomeAudio() {
    return new Promise<void>((resolve) => {
      const welcome = new Audio("/bienvenida.wav");

      const audioCtx = new (window.AudioContext ||
        (window as any).webkitAudioContext)();
      const source = audioCtx.createMediaElementSource(welcome);

      const analyzer = audioCtx.createAnalyser();
      analyzer.fftSize = 256;
      const bufferLength = analyzer.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      source.connect(analyzer);
      analyzer.connect(audioCtx.destination);

      setAnalyzerData({ analyzer, dataArray, bufferLength });

      setMsg((prev) => [
        ...prev,
        { role: "assistant", value: "Hola. ¿En qué puedo ayudarte hoy?" },
      ]);
      setStatus("Hablando");

      welcome.play();

      welcome.onended = () => {
        resolve();
      };
    });
  }

  useEffect(() => {
    return () => {
      // parar media stream (micrófono)
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }

      // cerrar websocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      // parar audios del asistente
      stopAssistantAudio();

      // cerrar AudioContext
      if (audioCtxRef.current) {
        audioCtxRef.current.close().catch(() => {});
        audioCtxRef.current = null;
      }

      // resetear refs
      partialBufRef.current = "";
      queueTimeRef.current = undefined;
      assistantSourcesRef.current = [];

      setAnalyzerData(null);
      setStatus("idle");
    };
  }, []);

  return { start, stop, status, analyzerData, setAnalyzerData };
}
