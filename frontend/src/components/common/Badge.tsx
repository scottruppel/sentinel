import { getRiskLevel, type RiskLevel } from '../../types';

const colors: Record<RiskLevel, string> = {
  critical: 'bg-risk-critical text-white',
  high: 'bg-risk-high text-white',
  medium: 'bg-risk-medium text-gray-900',
  low: 'bg-risk-low text-white',
};

const labels: Record<RiskLevel, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

interface RiskBadgeProps {
  score: number;
  showScore?: boolean;
  size?: 'sm' | 'md';
}

export default function RiskBadge({ score, showScore = true, size = 'md' }: RiskBadgeProps) {
  const level = getRiskLevel(score);
  const sizeClass = size === 'sm' ? 'text-xs px-1.5 py-0.5' : 'text-sm px-2 py-1';

  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${colors[level]} ${sizeClass}`}>
      {labels[level]}
      {showScore && <span className="opacity-80">({Math.round(score)})</span>}
    </span>
  );
}

interface DeltaIndicatorProps {
  delta: number;
}

export function DeltaIndicator({ delta }: DeltaIndicatorProps) {
  if (Math.abs(delta) < 0.1) return <span className="text-gray-400">—</span>;
  const isUp = delta > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-sm font-medium ${isUp ? 'text-risk-critical' : 'text-risk-low'}`}>
      {isUp ? '↑' : '↓'} {Math.abs(Math.round(delta))}
    </span>
  );
}
