import { Header } from "@/components/custom/header";
import { useVoiceAssistant } from "./hooks/useVoice";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { motion } from "framer-motion";
import { Message } from "@/interfaces/interfaces";

type Props = {};

export default function Avatar({}: Props) {
  const [msg, setMsg] = useState<Message[]>([]);
  const [isOpen, setIsOpen] = useState<boolean>(true);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const { start, status, stop, setAnalyzerData, mediaStreamRef } = useVoiceAssistant({
    setMsg: setMsg,
  });

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [msg]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msg]);

  return (
    <div className="flex flex-col w-full h-dvh bg-background">
      {/* Header fijo arriba */}
      <div className="w-full h-fit">
        <Header />
      </div>

      {/* Cuerpo: avatar + chat en columnas */}
      <div className="flex flex-col lg:flex-row flex-1 gap-4 p-2 overflow-hidden">
        {/* Avatar */}
        <div className="flex-1 flex flex-col relative">
          <div className="flex-1 flex justify-center items-center border border-input bg-muted rounded-2xl shadow relative overflow-hidden bg-white">
            <img
              src="/logo_completo.png"
              alt="Logo Bancoomeva"
              className="absolute top-2 left-2 z-10"
              width={150}
            />

            <img
              src="/avatar/vega-2 (1).png"
              className={`h-[80%] object-contain ${
                status == "Hablando"
                  ? "opacity-100"
                  : "opacity-0 -z-10 absolute pointer-events-none"
              }`}
              alt="avatar"
            />
            <img
              src="/avatar/vega 3 (1).png"
              className={`h-[80%] object-contain ${
                status == "Hablando"
                  ? "opacity-0 -z-10 absolute pointer-events-none"
                  : "opacity-100"
              }`}
              alt="avatar"
            />

            {/* Botón control */}
          </div>
          <div className="absolute z-10 bottom-0 w-full h-fit flex flex-row px-10 py-2">
            <button
              className={`m-auto cursor-pointer border border-input bg-[#444444] shadow-lg rounded-full p-2 grid place-content-center ${
                mediaStreamRef?.current == null ? "" : "bg-red-500 !fill-white"
              }`}
              onClick={() => {
                console.log(mediaStreamRef)
                if (mediaStreamRef?.current == null) {
                  start();
                } else {
                  stop();
                  setAnalyzerData(null);
                }
              }}
            >
              {mediaStreamRef?.current == null ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke={"white"}
                  width={40}
                  height={40}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
                  />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke={"white"}
                  width={40}
                  height={40}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5.25 7.5A2.25 2.25 0 0 1 7.5 5.25h9a2.25 2.25 0 0 1 2.25 2.25v9a2.25 2.25 0 0 1-2.25 2.25h-9a2.25 2.25 0 0 1-2.25-2.25v-9Z"
                  />
                </svg>
              )}
            </button>
            <button
              className={`p-2 shadow rounded flex justify-center items-center border border-neutral-300 ${
                isOpen ? "bg-[#008d44]" : "bg-muted"
              }`}
              onClick={() => setIsOpen((prev) => !prev)}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke={isOpen ? "#fff" : "#444444"}
                width={40}
                height={40}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Chat */}
        <div
          className={`flex flex-col gap-4 border border-input bg-white p-2 px-4 rounded-xl shadow-lg transition-all duration-500 ease-in-out relative lg:h-full
    ${isOpen ? "h-2/6 lg:w-4/12" : "h-0 lg:w-0 opacity-0"}
  `}
        >
          {isOpen && <h1 className="font-bold text-xl">Conversación</h1>}

          <div
            ref={chatContainerRef}
            className={`flex-1 flex flex-col overflow-y-auto space-y-2 relative transition-all duration-200 ${
              isOpen ? "opacity-100" : "opacity-0"
            }`}
          >
            {msg.map((m, i) => (
              <AnimatePresence key={i}>
                <motion.span
                  className={`p-2 rounded shadow w-fit max-w-[80%] ${
                    m.role === "assistant"
                      ? "bg-[#008d44] text-white self-start"
                      : "bg-[#444444] text-white self-end"
                  }`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  {m.value}
                </motion.span>
              </AnimatePresence>
            ))}

            {/* 🔽 Este div invisible marca el final */}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
