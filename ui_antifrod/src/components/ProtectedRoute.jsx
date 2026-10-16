import React from 'react';
import { Outlet } from 'react-router-dom';
import { useAuth } from '@/libs/AuthContext';

export default function ProtectedRoute({ unauthenticatedElement }) {
  const { isAuthenticated, isLoadingAuth } = useAuth();

  if (isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-800 rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return unauthenticatedElement || null;
  }

  return <Outlet />;
}