import { Header } from "@/components/custom/header";
import { Link } from "react-router-dom";

type Props = {};

export default function Welcome({}: Props) {
  return (
    <div className="flex flex-col min-w-0 h-dvh bg-background items-center">
      <Header />
      <div className="flex-1 flex flex-col justify-center items-center text-center space-y-6 w-full px-4">
        <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
          Bienvenido a tu asistente digital
        </p>

        {/* Contenedor de tarjetas */}
        <div className="flex flex-col md:flex-row gap-6 w-full max-w-3xl items-stretch">
          {/* Avatar */}
          <Link
            to="/avatar"
            className="flex-1 flex flex-col items-center justify-between gap-3 rounded-xl border border-gray bg-background p-4 text-gray-700 dark:text-gray-200 hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <img
              src="/image.png"
              alt="Avatar"
              className="h-[120px] object-contain"
            />
            <span className="font-bold text-lg">Avatar</span>
            <p className="text-sm text-center flex-1">
              Un asistente visual que puede interactuar contigo con voz y
              gestos.
            </p>
          </Link>

          {/* Agente */}
          <Link
            to="/chat"
            className="flex-1 flex flex-col items-center justify-between gap-3 rounded-xl border border-gray bg-background p-4 text-gray-700 dark:text-gray-200 hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <img
              src="/image1.png"
              alt="Agente SQL"
              className="h-[120px] object-contain"
            />
            <span className="font-bold text-lg">Agente SQL</span>
            <p className="text-sm text-center flex-1">
              Un asistente especializado en consultas SQL que te ayuda a crear y
              optimizar queries.
            </p>
          </Link>
        </div>
      </div>
    </div>
  );
}
