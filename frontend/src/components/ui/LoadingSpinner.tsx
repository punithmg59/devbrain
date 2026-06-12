interface LoadingSpinnerProps {
  size?: "small" | "medium" | "large";
  className?: string;
  label?: string;
  text?: string; // backward compatibility
}

export default function LoadingSpinner({
  size = "medium",
  className = "",
  label = "Loading...",
  text,
}: LoadingSpinnerProps) {
  const sizeClasses = {
    small: "w-4 h-4",
    medium: "w-8 h-8",
    large: "w-12 h-12",
  }[size];
  const displayLabel = text ?? label;

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div className={`border-4 border-gray-300 border-t-transparent rounded-full animate-spin ${sizeClasses}`} />
      {displayLabel && <p className="mt-2 text-sm text-gray-400">{displayLabel}</p>}
    </div>
  );
}


