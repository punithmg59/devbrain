import { useEffect, useState } from "react";
import { Github, Brain } from "lucide-react";
import { authService } from "../services/authService";
import { useNavigate } from "react-router-dom";

export default function GitHubLoginPage() {
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const checkToken = async () => {
      try {
        const tokenStatus = await authService.checkGitHubToken();
        if (tokenStatus) {
          navigate("/dashboard");
        }
      } catch {
        // No token, stay on login page
      } finally {
        setLoading(false);
      }
    };
    checkToken();
  }, [navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white flex flex-col">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Brain className="w-6 h-6 text-purple-500" />
          <span className="text-xl font-bold">DevBrain</span>
        </div>
      </nav>

      <div className="flex-1 flex items-center justify-center px-6">
        <div className="max-w-md w-full text-center">
          <div className="mb-8">
            <div className="w-20 h-20 bg-purple-600/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <Github className="w-10 h-10 text-purple-500" />
            </div>
            <h1 className="text-3xl font-bold mb-3">Connect with GitHub</h1>
            <p className="text-gray-400">
              Sign in with GitHub to connect your repositories and start analyzing your codebase with AI
            </p>
          </div>

          <button
            onClick={() => authService.loginWithGitHub()}
            className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-white text-gray-900 rounded-lg font-medium hover:bg-gray-100 transition-colors text-lg"
          >
            <Github className="w-5 h-5" />
            Sign in with GitHub
          </button>

          <div className="mt-8 pt-8 border-t border-gray-800">
            <p className="text-xs text-gray-500">
              By signing in, you agree to connect your GitHub repositories for analysis
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
