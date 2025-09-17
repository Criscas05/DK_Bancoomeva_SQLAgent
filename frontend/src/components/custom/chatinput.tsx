import { Textarea } from "../ui/textarea";
import { cx } from "classix";
import { Button } from "../ui/button";
import { ArrowUpIcon } from "./icons";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { useState } from "react";

// chatinput.tsx
interface ChatInputProps {
  question: string;
  setQuestion: (value: string) => void;
  onSubmit: (text?: string) => void;
  isLoading: boolean;
  instructions: string;
  setInstructions: (value: string) => void;
  hasStartedChat: boolean;
}

const suggestedActions = [
  {
    title: "¿Comparando el acumulado del año actual vs. el anterior, ",
    label:
      "cuál es la variación en ventas netas por kilos y pesos a total compañía?",
    action:
      "¿Comparando el acumulado del año actual vs. el anterior, cuál es la variación en ventas netas por kilos y pesos a total compañía?",
  },
  {
    title: "¿Cuál es la cadena con el mayor ",
    label:
      "porcentaje de descuentos sobre la venta neta en los últimos 3 meses?",
    action:
      "¿Cuál es la cadena con el mayor porcentaje de descuentos sobre la venta neta en los últimos 3 meses?",
  },
];

export const ChatInput = ({
  question,
  setQuestion,
  onSubmit,
  isLoading,
  instructions,
  setInstructions,
  hasStartedChat,
}: ChatInputProps) => {
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [showInstructions, setShowInstructions] = useState(false);

  return (
    <div className="relative w-full flex flex-col gap-4">
      {showSuggestions && !hasStartedChat && (
        <div className="hidden md:grid sm:grid-cols-2 gap-2 w-full">
          {suggestedActions.map((suggestedAction, index) => (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ delay: 0.05 * index }}
              key={index}
              className={index > 1 ? "hidden sm:block" : "block"}
            >
              <Button
                variant="ghost"
                onClick={() => {
                  setShowSuggestions(false);
                  setQuestion(suggestedAction.action);
                  onSubmit(suggestedAction.action);
                }}
                className="text-left border rounded-xl px-4 py-3.5 text-sm flex-1 gap-1 sm:flex-col w-full h-auto justify-start items-start"
              >
                <span className="font-medium">{suggestedAction.title}</span>
                <span className="text-muted-foreground">
                  {suggestedAction.label}
                </span>
              </Button>
            </motion.div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2 items-center justify-start">
        {/* Botón de ayuda */}
        <Button
          variant="outline"
          className="input-button-style w-full sm:w-auto"
          onClick={() => {
            toast.custom(
              (t) => (
                <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-xl p-4 shadow-lg w-full max-w-xs sm:max-w-sm md:max-w-md text-sm flex flex-col gap-2">
                  <div className="font-semibold text-base">
                    ¿Cómo usar el Agente SQL de Bancoomeva?
                  </div>
                  <div className="text-muted-foreground leading-relaxed">
                    1. Selecciona un <strong>catálogo</strong> de la lista.
                    <br />
                    2. Luego selecciona un <strong>esquema</strong> relacionado.
                    <br />
                    3. Escribe una pregunta como “¿Cual es el producto mas
                    vendido?”
                    <br />
                    4. Presiona <strong>Enter</strong> o el ícono de enviar.
                  </div>
                  <Button
                    size="sm"
                    className="self-end mt-2"
                    onClick={() => toast.dismiss(t)}
                  >
                    Cerrar
                  </Button>
                </div>
              ),
              { duration: Infinity }
            );
          }}
        >
          ℹ️ Ayuda
        </Button>
        <Button
          variant="outline"
          className="input-button-style w-full sm:w-auto"
          onClick={() => setShowInstructions((prev) => !prev)}
        >
          📝 Instrucciones
        </Button>
      </div>

      <input
        type="file"
        className="fixed -top-4 -left-4 size-0.5 opacity-0 pointer-events-none"
        multiple
        tabIndex={-1}
      />

      <Textarea
        placeholder="Escribe una consulta..."
        className={cx(
          "min-h-[24px] max-h-[calc(75dvh)] overflow-hidden resize-none rounded-xl text-base bg-muted"
        )}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();

            if (isLoading) {
              toast.error("Please wait for the model to finish its response!");
            } else {
              setShowSuggestions(false);
              onSubmit();
            }
          }
        }}
        rows={3}
        autoFocus
      />

      {showInstructions && (
        <div className="border rounded-xl p-4 mt-2 bg-muted relative">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold text-sm">
              Instrucciones adicionales
            </span>
            <Button
              size="sm"
              variant="ghost"
              className="text-xs"
              onClick={() => setShowInstructions(false)}
            >
              ✖ Cerrar
            </Button>
          </div>
          <Textarea
            placeholder="Especifica reglas o filtros que el agente debe seguir..."
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            className="bg-white dark:bg-zinc-800 text-base rounded-xl"
            rows={3}
          />
        </div>
      )}

      <Button
        className="rounded-full p-1.5 h-fit absolute bottom-2 right-2 m-0.5 border dark:border-zinc-600"
        onClick={() => onSubmit(question)}
        disabled={question.length === 0}
      >
        <ArrowUpIcon size={14} />
      </Button>
    </div>
  );
};
