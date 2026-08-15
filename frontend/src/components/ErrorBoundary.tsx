import React, { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
}

export default class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[APP_BOOT] ErrorBoundary caught an unhandled error:", error, info);
  }

  resetError = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      const errorMessage =
        this.state.error?.message ||
        this.props.fallbackMessage ||
        "An unexpected runtime error occurred. Please try again or return home.";

      return (
        <div className="min-h-screen bg-[#0f0f0f] text-white flex flex-col items-center justify-center p-6 text-center">
          <div className="max-w-md w-full bg-gray-900/80 border border-gray-800 rounded-2xl p-8 shadow-2xl flex flex-col items-center">
            <div className="w-12 h-12 rounded-full bg-red-950/60 border border-red-800/50 flex items-center justify-center mb-5">
              <AlertTriangle className="w-6 h-6 text-red-400" />
            </div>

            <h2 className="text-xl font-bold mb-2">
              {this.props.fallbackTitle || "Something went wrong"}
            </h2>

            <p className="text-sm text-gray-400 mb-6 break-words leading-relaxed font-mono bg-black/40 p-3 rounded-lg border border-gray-800/60 w-full text-left">
              {errorMessage}
            </p>

            <div className="flex items-center gap-3 w-full">
              <button
                onClick={this.resetError}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 rounded-xl text-sm font-medium transition-colors shadow-lg shadow-purple-900/20"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>

              <button
                onClick={() => {
                  window.location.href = "/";
                }}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-sm font-medium text-gray-300 transition-colors"
              >
                <Home className="w-4 h-4" />
                Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
