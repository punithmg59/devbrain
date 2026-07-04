interface CompactMetricProps {
  label: string;
  value: number | string;
}

export default function CompactMetric({ label, value }: CompactMetricProps) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-gray-900/30 border border-gray-800/50 rounded-lg">
      <span className="text-xs font-medium text-gray-500">{label}:</span>
      <span className="text-sm font-semibold text-gray-300">{value}</span>
    </div>
  );
}
