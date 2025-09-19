import { ChatInput } from "@/components/custom/chatinput";
import { useScrollToBottom } from "@/components/custom/use-scroll-to-bottom";
import { useState } from "react";
import { Overview } from "@/components/custom/overview";
import { Header } from "@/components/custom/header";
import { v4 as uuidv4 } from "uuid";
import Editor from "react-simple-code-editor";
import { useTheme } from "@/context/ThemeContext";
import * as prism from "prismjs";
import "prismjs/components/prism-sql";
import "prismjs/components/prism-sql";
import "prismjs/themes/prism.css";
import { EChartsWrapper } from "@/components/custom/EchartsWrapper";
import ReactMarkdown from "react-markdown";
import {
  Download,
  FilePenLine,
  Save,
  TableProperties,
  BarChart3,
  Play,
} from "lucide-react";
import { useEffect } from "react";
import remarkGfm from "remark-gfm";

interface AssistantMessage {
  id: string;
  answer: string;
  table: { [key: string]: string }[];
  columns: string[];
  sql: string;
  sql_results_download_url: string;
}

const formatSQL = (sql: string): string => {
  return sql
    .replace(
      /(SELECT|FROM|JOIN|WHERE|GROUP BY|ORDER BY|HAVING|LIMIT)/gi,
      "\n$1"
    )
    .replace(/,/g, ",\n")
    .trim();
};

const printTable = (msg: AssistantMessage) => {
  const { columns, table } = msg;

  if (!columns || !Array.isArray(columns) || !table || !Array.isArray(table)) {
    console.error("Datos inválidos para imprimir la tabla.");
    return;
  }

  const htmlTable = `
    <table border="1" style="border-collapse: collapse; width: 100%; font-family: sans-serif;">
      <thead>
        <tr>${columns.map((col) => `<th>${col}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${table
          .map(
            (row) => `
          <tr>${columns
            .map((col) => `<td>${row[col] || ""}</td>`)
            .join("")}</tr>
        `
          )
          .join("")}
      </tbody>
    </table>
  `;

  const newWin = window.open("", "Print-Window");
  if (newWin) {
    newWin.document.open();
    newWin.document.write(`
      <html><head><title>Impresión de tabla</title></head>
      <body onload="window.print()">
        ${htmlTable}
      </body></html>
    `);
    newWin.document.close();
  }
};

const downloadCSV = (msg: AssistantMessage) => {
  const link = document.createElement("a");
  link.href = msg.sql_results_download_url;
  link.setAttribute("download", "tabla.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export function Chat() {
  const [messagesContainerRef, messagesEndRef] =
    useScrollToBottom<HTMLDivElement>();
  const [question, setQuestion] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [userMessages, setUserMessages] = useState<
    { content: string; id: string }[]
  >([]);
  const [showSQL, setShowSQL] = useState<{ [id: string]: boolean }>({});
  const { isDarkMode } = useTheme();
  const [showChart, setShowChart] = useState<{ [id: string]: boolean }>({});
  const [chartType, setChartType] = useState<{ [id: string]: string }>({});

  const [instructions, setInstructions] = useState<string>("");

  const [hasStartedChat, setHasStartedChat] = useState(false);
  const [sessionId, setSessionId] = useState("");

  const handleSubmit = async ({
    text = "",
    query = "",
    idMessageCorrected = "",
    isUpdate = false,
  }: {
    text?: string;
    query?: string;
    idMessageCorrected?: string;
    isUpdate?: boolean;
  }) => {
    if (isLoading) return;
    const messageId = idMessageCorrected || uuidv4();

    const messageText = text || question;

    if (!isUpdate) {
      setUserMessages((prev) => [
        ...prev,
        { content: messageText, id: messageId },
      ]);
    }
    setQuestion("");
    setHasStartedChat(true);

    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    }, 100);

    setIsLoading(true);

    let res: Response | null = null;

    try {
      // 🚀 1. PRIMERA PETICIÓN- la pregunta del usuario
      res = await fetch(`${import.meta.env.VITE_APP_API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_query: messageText, // 👈 uso el messageText enviado
          session_id: sessionId,
          message_id: messageId,
          ...(query ? { corrected_sql_query: query } : {}),
        }),
      });

      if (!res.ok) throw new Error("Error en /chat");

      const data = await res.json();
      const {
        response,
        sql_query,
        sql_results_download_url,
        session_id,
        message_id,
      } = data;

      // 🚀 2. SEGUNDA PETICIÓN (usa session_id y message_id retornados)
      const resSql = await fetch(
        `${
          import.meta.env.VITE_APP_API_URL
        }/get_sample_result/${session_id}/${message_id}`,
        {
          headers: { "Content-Type": "application/json" },
        }
      );

      if (!resSql.ok) throw new Error("Error en /get_result");

      const { columns, rows } = parseSQLResult(await resSql.json());

      // 🚀 3. Agregar mensajes o Actualizar
      if (isUpdate) {
        const updatedMessages = messages.map((m) =>
          m.id === idMessageCorrected
            ? {
                ...m,
                answer: response,
                columns,
                table: rows,
                sql_results_download_url,
                sql: formatSQL(sql_query),
              }
            : m
        );
        setMessages(updatedMessages);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: messageId,
            answer: response,
            columns, // aquí puedes mapear dataSql.columns
            table: rows, // aquí puedes mapear dataSql.rows
            sql: formatSQL(sql_query),
            sql_results_download_url,
          },
        ]);
      }
    } catch (error: any) {
      console.error("Error al contactar el backend:", error);

      const isTimeout = error.message.includes("timeout");
      const isServerError = res?.status && res.status >= 500;

      const friendlyMessage = isTimeout
        ? "Pensar una respuesta está tomando más tiempo de lo esperado. Por favor, intenta de nuevo un poco más tarde."
        : isServerError
        ? "Estoy teniendo algunos problemas técnicos. Intenta nuevamente en un momento, por favor."
        : "No pude procesar tu mensaje en esta ocasión. Por favor, intenta nuevamente en un rato o modifica tu pregunta. Si el problema persiste, por favor contacta con un administrador.";

      setMessages((prev) => [
        ...prev,
        {
          id: messageId,
          answer: friendlyMessage,
          columns: [],
          table: [],
          sql: "",
          sql_results_download_url: "",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const parseSQLResult = (
    sqlResult: any
  ): { columns: string[]; rows: any[] } => {
    try {
      return {
        columns: sqlResult.columns || [],
        rows: sqlResult.rows || [],
      };
    } catch (e) {
      console.error("Error parseando sql_result:", e);
      return { columns: [], rows: [] };
    }
  };

  const renderChart = (
    msg: AssistantMessage,
    type: string,
    x: string = "",
    y: string = ""
  ) => {
    const data = msg.table.map((row) => {
      const newRow: any = { ...row };
      msg.columns.slice(1).forEach((key) => {
        newRow[key] =
          typeof row[key] === "string" || typeof row[key] === "number"
            ? parseFloat(String(row[key]).replace(/[^0-9.-]+/g, "")) || 0
            : 0;
      });
      return newRow;
    });

    if (!data || data.length === 0) return null;

    return (
      <div className="my-4">
        <EChartsWrapper
          key={`${msg.id}-${type}`}
          data={data}
          columns={msg.columns}
          chartType={type}
          x={x}
          y={y}
        />
      </div>
    );
  };

  useEffect(() => {
    setSessionId(uuidv4());
  }, []);

  return (
    <div className="flex flex-col min-w-0 h-dvh bg-background items-center">
      <Header />
      <div
        className="flex flex-col w-full max-w-5xl gap-6 flex-1 overflow-y-scroll pt-4 px-6 scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100 dark:scrollbar-thumb-gray-600 dark:scrollbar-track-zinc-800"
        ref={messagesContainerRef}
      >
        {userMessages.length === 0 && <Overview />}
        {userMessages.map((userMsg) => {
          const assistantMsg = messages.find((m) => m.id === userMsg.id);
          return (
            <div key={userMsg.id} className="space-y-4">
              <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg border border-gray-300 dark:border-gray-600 shadow-sm">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  🙋‍♂️ Usuario:
                </p>
                <p className="text-base text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
                  {userMsg.content}
                </p>
              </div>

              {assistantMsg && (
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-300 dark:border-gray-600 shadow-inner">
                  <p className="text-sm font-medium text-indigo-700 dark:text-indigo-300 mb-2">
                    🤖 Asistente:
                  </p>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    className="prose dark:prose-invert max-w-none text-gray-800 dark:text-gray-100 mb-4"
                  >
                    {assistantMsg.answer}
                  </ReactMarkdown>
                  {assistantMsg.table.length > 0 && (
                    <div className="overflow-x-auto mb-4">
                      <table
                        id={`table-${assistantMsg.id}`}
                        className="min-w-full text-sm border border-collapse border-gray-300 bg-white rounded shadow-sm"
                      >
                        <thead>
                          <tr>
                            {assistantMsg.columns.map((col) => (
                              <th
                                key={col}
                                className="border px-3 py-2 bg-gray-100 dark:bg-gray-700 text-left text-gray-700 dark:text-gray-100"
                              >
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {assistantMsg.table.map((row, idx) => (
                            <tr key={idx}>
                              {assistantMsg.columns.map((col) => (
                                <td
                                  key={col}
                                  className="border px-3 py-2 bg-gray-100 dark:bg-gray-700 text-left text-gray-700 dark:text-gray-100"
                                >
                                  {row[col]}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {showChart[assistantMsg.id] &&
                        chartType[assistantMsg.id] && (
                          <>
                            <div className="mt-4">
                              {renderChart(
                                assistantMsg,
                                chartType[assistantMsg.id]
                              )}
                            </div>
                          </>
                        )}
                    </div>
                  )}

                  <div className="flex flex-wrap justify-end gap-2 mb-2">
                    <button
                      onClick={() => printTable(assistantMsg)}
                      className="p-2 rounded-md border dark:border-zinc-700 hover:bg-muted transition"
                      title="Imprimir tabla"
                    >
                      <TableProperties size={18} />
                    </button>

                    {assistantMsg.sql_results_download_url && (
                      <button
                        onClick={() => downloadCSV(assistantMsg)}
                        className="p-2 rounded-md border dark:border-zinc-700 hover:bg-muted transition"
                        title="Descargar CSV"
                      >
                        <Download size={18} />
                      </button>
                    )}
                    {assistantMsg.sql && (
                      <button
                        onClick={() =>
                          setShowSQL((prev) => ({
                            ...prev,
                            [assistantMsg.id]: !prev[assistantMsg.id],
                          }))
                        }
                        className="p-2 rounded-md border dark:border-zinc-700 hover:bg-muted transition"
                        title={
                          showSQL[assistantMsg.id]
                            ? "Ocultar SQL"
                            : "Mostrar SQL"
                        }
                      >
                        <FilePenLine size={18} />
                      </button>
                    )}

                    {assistantMsg.table.length &&
                    assistantMsg.columns.length > 1 ? (
                      <button
                        onClick={() => {
                          setShowChart((prev) => ({
                            ...prev,
                            [assistantMsg.id]: !prev[assistantMsg.id],
                          }));
                          setChartType((prev) => ({
                            ...prev,
                            [assistantMsg.id]: prev[assistantMsg.id] || "Bar",
                          }));
                        }}
                        className="p-2 rounded-md border dark:border-zinc-700 hover:bg-muted transition"
                        title={
                          showChart[assistantMsg.id]
                            ? "Ocultar gráfico"
                            : "Mostrar gráfico"
                        }
                      >
                        <BarChart3 size={18} />
                      </button>
                    ) : (
                      <></>
                    )}

                    {showChart[assistantMsg.id] && (
                      <select
                        className="px-2 py-1 text-sm border border-gray-300 rounded-md dark:bg-gray-700 dark:text-white"
                        value={chartType[assistantMsg.id] || "Bar"}
                        onChange={(e) =>
                          setChartType((prev) => ({
                            ...prev,
                            [assistantMsg.id]: e.target.value,
                          }))
                        }
                      >
                        <option value="Bar">BarChart</option>
                        <option value="Line">LineChart</option>
                        <option value="Pie">PieChart</option>
                        <option value="Radar">RadarChart</option>
                      </select>
                    )}
                  </div>

                  {showSQL[assistantMsg.id] && (
                    <div className="mt-2 space-y-2">
                      <Editor
                        value={assistantMsg.sql}
                        onValueChange={(code) => {
                          const updatedMessages = messages.map((m) =>
                            m.id === assistantMsg.id ? { ...m, sql: code } : m
                          );
                          setMessages(updatedMessages);
                        }}
                        highlight={(code) =>
                          prism.highlight(code, prism.languages.sql, "sql")
                        }
                        padding={10}
                        className={`w-full text-sm font-mono rounded-md border ${
                          isDarkMode
                            ? "bg-[#1e1e1e] text-white border-gray-600"
                            : "bg-white text-black border-gray-300"
                        }`}
                        style={{
                          backgroundColor: isDarkMode ? "#1e1e1e" : "#f8f8f8",
                          minHeight: "200px",
                          whiteSpace: "pre-wrap",
                        }}
                      />

                      <div className="flex gap-2">
                        <button
                          onClick={async () => {
                            handleSubmit({
                              text: userMsg.content,
                              query: assistantMsg.sql,
                              idMessageCorrected: assistantMsg.id,
                              isUpdate: true,
                            });
                          }}
                          className="p-2 rounded-md border dark:border-zinc-700 hover:bg-muted transition"
                          title="Ejecutar esta consulta"
                        >
                          <Play size={18} />
                        </button>

                        <button
                          onClick={async () => {
                            try {
                              const token =
                                sessionStorage.getItem("accessToken");

                              const res = await fetch(
                                `${
                                  import.meta.env.VITE_APP_API_URL
                                }/api/save-sql`,
                                {
                                  method: "POST",
                                  headers: {
                                    "Content-Type": "application/json",
                                    Authorization: `Bearer ${token}`,
                                    accept: "application/json",
                                  },
                                  body: JSON.stringify({
                                    question: userMsg.content,
                                    sql_query: assistantMsg.sql,
                                  }),
                                }
                              );
                              if (!res.ok)
                                throw new Error("Error al guardar la consulta");
                              alert("Consulta guardada correctamente ✅");
                            } catch (err) {
                              console.error(
                                "Error al guardar la consulta:",
                                err
                              );
                              alert("❌ Error al guardar la consulta");
                            }
                          }}
                          className="p-2 rounded-md border dark:border-zinc-700 hover:bg-muted transition"
                          title="Guardar esta consulta"
                        >
                          <Save size={18} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {isLoading && (
          <div className="text-center text-gray-500 italic">⏳ Pensando...</div>
        )}

        <div
          ref={messagesEndRef}
          className="shrink-0 min-w-[24px] min-h-[24px]"
        />
      </div>

      <div className="flex mx-auto px-4 bg-background pb-4 md:pb-6 gap-2 w-full md:max-w-5xl">
        <ChatInput
          question={question}
          setQuestion={setQuestion}
          onSubmit={handleSubmit}
          isLoading={isLoading}
          instructions={instructions}
          setInstructions={setInstructions}
          hasStartedChat={hasStartedChat}
        />
      </div>
    </div>
  );
}
