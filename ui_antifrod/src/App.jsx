import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/libs/query-client'
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import PageNotFound from '@/libs/PageNotFound';
import { AuthProvider, useAuth } from '@/libs/AuthContext';
import ScrollToTop from '@/components/ScrollToTop';
import ProtectedRoute from '@/components/ProtectedRoute';
import AppShell from '@/components/layout/AppShell';
import Dashboard from '@/pages/Dashboard';
import Calls from '@/pages/Calls';
import CallDetail from '@/pages/CallDetail';
import CallProtocol from '@/pages/CallProtocol';
import Numbers from '@/pages/Numbers';
import NumberDetail from '@/pages/NumberDetail';
import GraphView from '@/pages/GraphView';
import Blocks from '@/pages/Blocks';
import Rules from '@/pages/Rules';
import Profile from '@/pages/Profile';
import CdrRecords from '@/pages/CdrRecords';
import Login from '@/pages/Login';
import ForgotPassword from '@/pages/ForgotPassword';
import ResetPassword from '@/pages/ResetPassword';

const AuthenticatedApp = () => {
  const { isLoadingAuth } = useAuth();

  if (isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-800 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<ProtectedRoute unauthenticatedElement={<Navigate to="/login" replace />} />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/calls" element={<Calls />} />
          <Route path="/calls/:id" element={<CallDetail />} />
          <Route path="/numbers" element={<Numbers />} />
          <Route path="/numbers/:id" element={<NumberDetail />} />
          <Route path="/graph" element={<GraphView />} />
          <Route path="/blocks" element={<Blocks />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/cdr" element={<CdrRecords />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="/calls/:id/protocol" element={<CallProtocol />} />
      </Route>
      <Route path="*" element={<PageNotFound />} />
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router>
          <ScrollToTop />
          <AuthenticatedApp />
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  )
}

export default App