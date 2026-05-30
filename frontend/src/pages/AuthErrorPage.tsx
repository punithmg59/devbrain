import { Link, useSearchParams } from "react-router-dom";

const messages: Record<string, string> = {
  invalid_state: "Authentication failed. Please try again.",
  token_exchange_failed: "Could not connect to GitHub. Please try again.",
};

export default function AuthErrorPage() {
  const [searchParams] = useSearchParams();
  const msg = searchParams.get("msg") ?? "";
  const message = messages[msg] ?? "Something went wrong.";

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white flex flex-col items-center justify-center px-6">
      <div className="max-w-md text-center">
        <h1 className="text-2xl font-bold mb-4">Authentication Error</h1>
        <p className="text-gray-400 mb-8">{message}</p>
        <Link
          to="/"
          className="inline-block px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-medium transition-colors"
        >
          Try Again
        </Link>
      </div>
    </div>
  );
}
