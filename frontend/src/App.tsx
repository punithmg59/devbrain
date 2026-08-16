import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import useAuthStore from "./hooks/useAuthStore";
import { ToastProvider } from "./components/Toast";
import ErrorBoundary from "./components/ErrorBoundary";
import HomePage from "./pages/HomePage";
import DashboardPage from "./pages/DashboardPage";
import RepoDetailPage from "./pages/RepoDetailPage";
import ImpactRadarPage from "./pages/ImpactRadarPage";
import AuthErrorPage from "./pages/AuthErrorPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const initialized = useAuthStore((s) => s.initialized);
  const loading = useAuthStore((s) => s.loading);

  if (!initialized || loading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex flex-col items-center justify-center gap-3 text-white">
        <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-gray-400 font-mono">Authenticating session...</p>
      </div>
    );
  }

  if (!user) {
    console.log("[AUTH_BOOT] ProtectedRoute: unauthenticated user, redirecting to /");
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

function App() {
  const initialize = useAuthStore((s) => s.initialize);
  const initialized = useAuthStore((s) => s.initialized);
  const loading = useAuthStore((s) => s.loading);

  useEffect(() => {
    console.log("[APP_BOOT] App mounted, initializing auth state...");
    initialize();
  }, [initialize]);

  if (!initialized || loading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex flex-col items-center justify-center gap-3 text-white">
        <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-gray-400 font-mono">Loading DevBrain...</p>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ToastProvider>
        <Routes>
          <Route
            path="/"
            element={
              <ErrorBoundary fallbackTitle="Home Page Error">
                <HomePage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <ErrorBoundary fallbackTitle="Dashboard Error">
                  <DashboardPage />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          <Route
            path="/repos/:repoId"
            element={
              <ProtectedRoute>
                <ErrorBoundary fallbackTitle="Repository Detail Error">
                  <RepoDetailPage />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          <Route
            path="/repos/:repoId/impact"
            element={
              <ProtectedRoute>
                <ErrorBoundary fallbackTitle="Impact Radar Error">
                  <ImpactRadarPage />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          <Route path="/auth/error" element={<AuthErrorPage />} />
          {/* Catch-all fallback route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
