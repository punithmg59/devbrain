import React from "react";

interface LoadingSpinnerProps {
  size?: "small" | "medium" | "large";
  className?: string;
  label?: string;
}

export default function LoadingSpinner({
  size = "medium",
  className = "",
  label = "Loading...",
}: LoadingSpinnerProps) {
  const sizeClasses = {
    small: "w-4 h-4",
    medium: "w-8 h-8",
    large: "w-12 h-12",
  }[size];

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div className={`border-4 border-gray-300 border-t-transparent rounded-full animate-spin ${sizeClasses}`} />
      {label && <p className="mt-2 text-sm text-gray-400">{label}</p>}
    </div>
  );
}
