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

  const { start, status, stop, setAnalyzerData } = useVoiceAssistant({
    setMsg: setMsg,
  });

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [msg]);
  console.log(msg);

  return (
    <div className="flex flex-col w-full h-dvh bg-background">
      {/* Header fijo arriba */}
      <div className="w-full h-fit">
        <Header />
      </div>

      {/* Cuerpo: avatar + chat en columnas */}
      <div className="flex flex-1 gap-4 p-2 overflow-hidden">
        {/* Avatar */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 flex justify-center items-center border border-input bg-muted rounded-2xl shadow relative overflow-hidden">
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
          <button
            className={`flex mx-auto my-2 cursor-pointer border border-input bg-muted shadow  rounded-full p-2 ${
              status === "Conectando" ? "waves" : ""
            }`}
            onClick={() => {
              if (status === "idle") {
                start();
              } else {
                stop();
                setAnalyzerData(null);
              }
            }}
            disabled={status === "Conectando"}
          >
            {status == "idle" || status == "Conectando" ? (
              <svg width={40} height={40} viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
                />
              </svg>
            ) : (
              <svg width={40} height={40} viewBox="0 0 24 24">
                <path
                  fillRule="evenodd"
                  d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9Z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </button>
        </div>

        {/* Chat */}
        <div
          className={`flex flex-col h-full gap-4 border border-input bg-muted p-2 px-4 rounded-xl shadow-lg transition-all duration-500 ease-in-out relative ${
            isOpen ? "w-4/12" : "w-16"
          }`}
        >
          {/* Toggle */}
          <button
            className="absolute top-9 -left-3.5 z-10 border border-input bg-muted rounded-full shadow border-neutral-200 p-2"
            onClick={() => setIsOpen((prev) => !prev)}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              width={16}
              height={16}
              className={`transform transition-transform duration-500 ${
                isOpen ? "rotate-180" : "rotate-0"
              }`}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 19.5 8.25 12l7.5-7.5"
              />
            </svg>
          </button>

          {isOpen && <h1 className="font-bold text-xl">Conversación</h1>}

          {/* Contenedor mensajes con scroll interno */}
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
                      ? "bg-[#084023] text-white self-start"
                      : "bg-[#645d5d] text-white self-end"
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
          </div>
        </div>
      </div>
    </div>
  );
}
