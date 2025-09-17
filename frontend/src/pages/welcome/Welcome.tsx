import { Header } from "@/components/custom/header";
import { Link } from "react-router-dom";

type Props = {};

export default function Welcome({}: Props) {
  return (
    <div className="flex flex-col min-w-0 h-dvh bg-background items-center">
      <Header />
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 w-full">
        <div className="w-full h-full text-[#B12923] flex flex-col justify-center items-center relative text-center gap-4">
          <Link
            to="/chat"
            className="w-4/12 text-nowrap flex flex-row gap-2 justify-center items-center border-[2px] text-white bg-[#B12923] px-4 py-2 rounded-full"
          >
            <span className="font-medium text-[1.0em] lg:text-[1.4em]">Ir al agente</span>
          </Link>
          <p className="w-8/12 text-[1.2em] font-normal">
            Un asistente que te apoya en la generación de reportes de clientes
          </p>
        </div>
        <div className="w-full bg-[#B12923] h-full text-white flex flex-col justify-center items-center relative text-center gap-4">
          <p className="w-8/12 text-[1.2em] font-normal">
            Un asistente visual que puede interactuar contigo de voz y gestos
          </p>
          <Link
            to="/avatar"
            className="w-4/12 text-nowrap flex flex-row gap-2 justify-center items-center border-[2px] text-[#B12923] bg-white border-white px-4 py-2 rounded-full z-10"
          >
            <span className="font-medium text-[1.0em] lg:text-[1.4em]">Habla con Vega</span>
          </Link>
          <img
            src="/avatar/vega 3 (1).png"
            alt="Avatar"
            className="h-[50%] object-contain absolute bottom-0 right-0"
          />
        </div>
        {/* Contenedor de tarjetas */}
        {/* <div className="flex flex-col md:flex-row gap-6 w-full max-w-3xl items-stretch">
          <Link
            to="/avatar"
            className="flex-1 flex flex-col items-center justify-between gap-3 rounded-xl border border-gray bg-background p-4 text-gray-700 dark:text-gray-200 hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <img
              src="/avatar/vega-6 (1).png"
              alt="Avatar"
              className="h-[120px] object-contain"
            />
            <span className="font-bold text-lg">Habla con Vega</span>
          </Link>

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
          </Link>
        </div> */}
      </div>
    </div>
  );
}
