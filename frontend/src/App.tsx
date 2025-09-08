// src/App.tsx
import "./App.css";
import { Chat } from "./pages/chat/chat";
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
} from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import { Toaster } from "sonner";
import Welcome from "./pages/welcome/Welcome";
import Avatar from "./pages/Avatar/Avatar";

// const RedirectToChat = () => {
//   const navigate = useNavigate();

//   useEffect(() => {
//     navigate("/chat", { replace: true });
//   }, [navigate]);

//   return null;
// };

const routerAuth = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/welcome" replace />,
  },
  {
    path: "/welcome",
    element: <Welcome />,
  },
  {
    path: "/chat",
    element: <Chat />,
  },
  {
    path: "/avatar",
    element: <Avatar />,
  },
  {
    path: "*", // Redirección para rutas no existentes
    element: <Navigate to="/" replace />,
  },
]);

// const routerPublic = createBrowserRouter([
//   {
//     path: "/",
//     element: <Navigate to="/login" replace />,
//   },
//   {
//     path: "/login",
//     element: <Login />,
//   },
//   {
//     path: "*", // Redirección para rutas no existentes
//     element: <Navigate to="/" replace />,
//   },
// ]);

function App() {
  return (
    <ThemeProvider>
      <div className="w-full h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
        <RouterProvider router={routerAuth} />
        {/* <Chat /> */}
        <Toaster position="top-right" richColors />
      </div>
    </ThemeProvider>
  );
}

export default App;

// Sin login

// import './App.css'
// import { Chat } from './pages/chat/chat'
// import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
// import { ThemeProvider } from './context/ThemeContext'
// import { Toaster } from 'sonner';

// function App() {
//   return (
//     <ThemeProvider>
//       <Router>
//         <div className="w-full h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
//           <Routes>
//             <Route path="/" element={<Chat />} />
//           </Routes>
//           <Toaster position="top-right" richColors />
//         </div>
//       </Router>
//     </ThemeProvider>
//   )
// }

// export default App;
