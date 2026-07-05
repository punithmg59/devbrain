import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import useAuthStore from "./hooks/useAuthStore";
import { ToastProvider } from "./components/Toast";
import ErrorBoundary from "./components/ErrorBoundary";
import HomePage from "./pages/HomePage";
import DashboardPage from "./pages/DashboardPage";
import RepoDetailPage from "./pages/RepoDetailPage";
import ImpactRadarPage from "./pages/ImpactRadarPage";
import ArchitectureExplorerPage from "./pages/ArchitectureExplorerPage";
import AuthErrorPage from "./pages/AuthErrorPage";
import GitHubLoginPage from "./pages/GitHubLoginPage";
import { authService } from "./services/authService";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const initialized = useAuthStore((s) => s.initialized);

  if (!initialized) return null;
  if (!user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function GitHubTokenCheck({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const [hasToken, setHasToken] = useState<boolean | null>(null);

  useEffect(() => {
    if (!user) {
      setHasToken(null);
      return;
    }
    authService.checkGitHubToken()
      .then(setHasToken)
      .catch(() => setHasToken(false));
  }, [user]);

  if (!user) return <>{children}</>;
  if (hasToken === null) return null;
  if (!hasToken) return <GitHubLoginPage />;
  return <>{children}</>;
}

function App() {
  const initialize = useAuthStore((s) => s.initialize);
  const initialized = useAuthStore((s) => s.initialized);
  const loading = useAuthStore((s) => s.loading);

  useEffect(() => {
    initialize();
  }, [initialize]);

  if (!initialized || loading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <ToastProvider>
      <GitHubTokenCheck>
        <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/github-login"
          element={<GitHubLoginPage />}
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/repos/:repoId"
          element={
            <ProtectedRoute>
              <ErrorBoundary>
                <RepoDetailPage />
              </ErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/repos/:repoId/impact"
          element={
            <ProtectedRoute>
              <ImpactRadarPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/repos/:repoId/architecture"
          element={
            <ProtectedRoute>
              <ErrorBoundary>
                <ArchitectureExplorerPage />
              </ErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route path="/auth/error" element={<AuthErrorPage />} />
      </Routes>
      </GitHubTokenCheck>
    </ToastProvider>
  );
}

export default App;
