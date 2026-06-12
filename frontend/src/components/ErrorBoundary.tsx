import { Component, ReactNode } from "react";
import ErrorState from "./ErrorState";

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

interface ErrorBoundaryProps {
  children: ReactNode;
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

  componentDidCatch(error: Error, info: unknown) {
    console.error("ErrorBoundary caught an error:", error, info);
  }

  resetError = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      return (
        <ErrorState
          message={
            this.state.error?.message ??
            "An unexpected error occurred while loading this repository."
          }
          retry={this.resetError}
        />
      );
    }

    return this.props.children;
  }
}
