import { Button } from "../ui/button";
import { Link, useNavigate } from "react-router-dom";

export const Header = () => {
  const navigate = useNavigate();
  function toBack() {
    navigate("/welcome", { replace: true });
  }
  const isWelcome = location.pathname.includes("welcome");

  return (
    <>
      <header
        className="flex items-center justify-between px-2 sm:px-4 py-2 bg-transparent z-50 text-black dark:text-white w-full"
        style={{
          position: isWelcome ? "fixed" : "relative",
        }}
      >
        <div className="flex items-center space-x-1 sm:space-x-2">
          {isWelcome && (
            <Link to="/">
              <img
                src="/logo_completo.png"
                alt="Logo Bancoomeva"
                className="w-[200px] object-contain mr-2"
              />
            </Link>
          )}
          {!isWelcome && (
            <Button
              variant="outline"
              className="bg-background border border-gray text-gray-600 hover:white dark:text-gray-200 h-10"
              onClick={toBack}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="size-6"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3"
                />
              </svg>
            </Button>
          )}
        </div>
      </header>
    </>
  );
};
