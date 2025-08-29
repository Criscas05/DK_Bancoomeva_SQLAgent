// // src/pages/Login.tsx
// import { useMsal } from '@azure/msal-react';
// import { loginRequest } from '../../config/msalConfig';

// export default function Login() {
//   const { instance } = useMsal();
//   const handleLogin = async () => {
//     try {
//       await instance.loginPopup(loginRequest);
//       // await instance.loginRedirect(loginRequest);
//       // redirige tras login
//       window.location.href = '/chat';
//     } catch (e) {
//       console.error('Error al iniciar sesión:', e);
//     }
//   };

//   return (
//     <div className="flex items-center justify-center h-screen">
//       <button onClick={handleLogin}>Iniciar con Microsoft</button>
//     </div>
//   );
// }


// src/pages/Login.tsx
import { useMsal } from '@azure/msal-react';
import { loginRequest } from '../../config/msalConfig';
import logo from '@/assets/logo.webp';
import logoMicrosoft from '@/assets/microsoft-logo.svg';
import loginBanner from '@/assets/login-banner.jpg'

export default function Login() {
  const { instance } = useMsal();

  const handleLogin = async () => {
    try {
      await instance.loginPopup(loginRequest); // Login en una ventana emergente sin recargar la página
      // await instance.loginRedirect(loginRequest); // Login con redirección del usuario a Microsoft y reload de la página

      const account = instance.getAllAccounts()[0];
      if (account) {
        const response = await instance.acquireTokenSilent({
          ...loginRequest,
          account,
        });
        sessionStorage.setItem("accessToken", response.accessToken);
      }

    } catch (e) {
      console.error('Error al iniciar sesión:', e);
    }
  };

  return (
    <div
      className="flex items-center justify-center h-screen bg-cover bg-center"
      style={{
        backgroundImage: `linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.65)), url(${loginBanner})`, //` url(https://alqueria.com.co/sites/default/files/styles/1320x680/public/2021-11/planta-banner-nosotros-historia-alqueria_0_0.jpg?h=37e3ef20&itok=bGb7Sp_n)`,
        backgroundSize: 'cover',
      }}>{/*"flex items-center justify-center h-screen bg-[#fae0de] text-white"*/}
      <div className="text-center min-w-[320px] max-w-[40%] flex flex-col items-center justify-around">
        {/* Logo de Alquería */}
        <img
          src= {logo}
          alt="Alquería Logo"
          className="mx-auto mb-8"
          style={{ width: '180px' }}
        />

        <h1 className="text-3xl font-bold text-white mb-4 tracking-wide leading-tight">
          ¡Te damos bienvenida al <span className="text-[#f8c346]">Agente SQL</span>!
        </h1>
        <p className="text-base text-gray-200 mb-8">
          Conecta, consulta y actúa: descubre lo que los datos tienen para contarte.
        </p>

        {/* Caja de inicio de sesión */}
        <div
          className="bg-[#ad0c10] p-10 rounded-xl shadow-xl inline-block flex flex-col items-center justify-between min-w-[300px] min-h-[215px] box-border"
          // style={{boxShadow: "rgba(31, 39, 45, 0.12) 0px 4px 16px"}}
          >
          <h2 className="text-2xl text-white font-semibold mb-6">Iniciar sesión</h2>

          <button
            onClick={handleLogin}
            className="w-full flex items-center justify-center gap-2 bg-white text-black px-4 py-2 rounded-md hover:bg-gray-200 transition font-medium"
          >
            <img
              src={logoMicrosoft}
              alt="Microsoft logo"
              className="w-5 h-5"
            />
            Iniciar sesión con Microsoft
          </button>

          <p className="text-sm text-white mt-4">
            Contacta al administrador para obtener acceso.
            {/* Si no puedes ingresar, por favor comunícate con soporte técnico. */}
          </p>
        </div>

        {/* Footer opcional */}
        <div className="mt-6 text-sm text-gray-500 flex justify-center gap-4">
          <a href="#" className="hover:underline">Aviso sobre privacidad</a>
          <a href="#" className="hover:underline">Mas sobre el Agente SQL</a>
        </div>
      </div>
    </div>
  );
}
