// src/components/PrivateRoute.tsx
import { Navigate } from 'react-router-dom';
import { useMsal } from '@azure/msal-react';

export function PrivateRoute({ children }: { children: JSX.Element }) {
  const { accounts } = useMsal();
  return children;
}
