import { useState, useRef, useEffect } from "react";
import { Sparkles, GitBranch } from "lucide-react";

interface CommandCenterProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  repoName?: string;
}

export default function CommandCenter({ value, onChange, onSubmit, repoName }: CommandCenterProps) {
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="relative">
      <div
        className={`relative bg-gradient-to-br from-gray-900/60 to-gray-800/40 border rounded-3xl p-6 backdrop-blur-sm transition-all duration-300 ${
          isFocused
            ? "border-purple-500/50 shadow-lg shadow-purple-500/10"
            : "border-gray-800/50 hover:border-gray-700/50"
        }`}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          {repoName && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/50 rounded-full">
              <GitBranch className="w-4 h-4 text-purple-400" />
              <span className="text-sm text-gray-300 truncate max-w-[200px]">{repoName}</span>
            </div>
          )}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/10 rounded-full">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-purple-400 font-medium">AI</span>
          </div>
        </div>

        {/* Input */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about this repository..."
          className="w-full bg-[#080808] border border-gray-800/50 rounded-2xl p-5 text-lg text-white placeholder-gray-600 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500/10 transition-all duration-200 min-h-[120px]"
          rows={1}
        />

        {/* Footer */}
        <div className="flex items-center justify-between mt-4">
          <div className="text-xs text-gray-600">
            <span className="text-gray-500">Press</span>
            <span className="ml-1 px-1.5 py-0.5 bg-gray-800/50 rounded text-gray-400">Enter</span>
            <span className="ml-1 text-gray-500">to ask</span>
            <span className="mx-2 text-gray-700">•</span>
            <span className="text-gray-500">Shift + Enter</span>
            <span className="ml-1 text-gray-500">for multiple lines</span>
          </div>
          <button
            onClick={onSubmit}
            disabled={!value.trim()}
            className="group flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:from-gray-800 disabled:-to-gray-800 disabled:text-gray-500 rounded-xl font-medium text-base transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/25 hover:-translate-y-0.5 disabled:hover:shadow-none disabled:hover:translate-y-0"
          >
            <Sparkles className="w-5 h-5 group-hover:rotate-12 transition-transform duration-300" />
            Ask
          </button>
        </div>
      </div>
    </div>
  );
}
