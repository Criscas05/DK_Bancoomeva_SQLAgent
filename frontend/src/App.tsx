// src/App.tsx
import './App.css';
import { Chat } from './pages/chat/chat';
import Login from './pages/login/Login';
import { createBrowserRouter, RouterProvider, Navigate, useNavigate } from "react-router-dom";
import { ThemeProvider } from './context/ThemeContext';
import { Toaster } from 'sonner';
import { MsalProvider, AuthenticatedTemplate, UnauthenticatedTemplate, } from '@azure/msal-react';
import { msalInstance } from './config/msalConfig';
import { useEffect } from "react";

const RedirectToChat = () => {
  const navigate = useNavigate();

  useEffect(() => {
    navigate("/chat", { replace: true });
  }, [navigate]);

  return null;
};

const routerAuth = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/chat" replace />,
  },
  {
    path: "/chat",
    element: <Chat />,
  },
  {
    path: "/auth/login-callback",
    element: <RedirectToChat />,
  },
  {
    path: "*", // Redirección para rutas no existentes
    element: <Navigate to="/" replace />,
  },
]);

const routerPublic = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/login" replace />,
  },
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "*", // Redirección para rutas no existentes
    element: <Navigate to="/" replace />,
  },
]);

function App() {
  return (
    <MsalProvider instance={msalInstance}>
      <ThemeProvider>
        <div className="w-full h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
          <UnauthenticatedTemplate>
            {/* <Login /> */}
            <RouterProvider router={routerPublic} />
          </UnauthenticatedTemplate>
          <AuthenticatedTemplate>
            <RouterProvider router={routerAuth} />
            {/* <Chat /> */}
          </AuthenticatedTemplate>
          <Toaster position="top-right" richColors />
        </div>
      </ThemeProvider>
    </MsalProvider>
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