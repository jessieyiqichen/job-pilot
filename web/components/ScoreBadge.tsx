'use client';

interface ScoreBadgeProps {
  score: number | null;
  size?: number;
}

export default function ScoreBadge({ score, size = 48 }: ScoreBadgeProps) {
  if (score == null) {
    return (
      <div
        className="flex items-center justify-center rounded-full bg-gray-100 text-gray-400"
        style={{ width: size, height: size, fontSize: size * 0.28 }}
      >
        --
      </div>
    );
  }

  const color = score >= 7 ? '#22c55e' : score >= 5 ? '#eab308' : '#ef4444';
  const radius = (size - 6) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 10) * circumference;

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={3}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={3}
          strokeDasharray={`${progress} ${circumference - progress}`}
          strokeLinecap="round"
        />
      </svg>
      <span
        className="absolute font-semibold"
        style={{ color, fontSize: size * 0.3 }}
      >
        {score.toFixed(1)}
      </span>
    </div>
  );
}
