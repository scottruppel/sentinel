import { useState } from 'react';
import { getRiskLevel } from '../../types';
import type { ComponentWithRisk } from '../../types';

const RISK_FILL: Record<string, string> = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
};

interface RiskHeatmapProps {
  components: ComponentWithRisk[];
  onSelect?: (component: ComponentWithRisk) => void;
}

export default function RiskHeatmap({ components, onSelect }: RiskHeatmapProps) {
  const [hovered, setHovered] = useState<ComponentWithRisk | null>(null);

  const sorted = [...components].sort(
    (a, b) => (b.risk_score?.composite_score ?? 0) - (a.risk_score?.composite_score ?? 0),
  );

  const cols = Math.ceil(Math.sqrt(sorted.length * 1.5));
  const cellSize = 28;
  const gap = 2;
  const rows = Math.ceil(sorted.length / cols);
  const width = cols * (cellSize + gap);
  const height = rows * (cellSize + gap);

  return (
    <div className="relative">
      <svg width={width} height={height} className="block">
        {sorted.map((comp, idx) => {
          const col = idx % cols;
          const row = Math.floor(idx / cols);
          const score = comp.risk_score?.composite_score ?? 0;
          const level = getRiskLevel(score);

          return (
            <rect
              key={comp.id}
              x={col * (cellSize + gap)}
              y={row * (cellSize + gap)}
              width={cellSize}
              height={cellSize}
              rx={3}
              fill={RISK_FILL[level]}
              opacity={hovered?.id === comp.id ? 1 : 0.85}
              stroke={hovered?.id === comp.id ? '#1e3a5f' : 'transparent'}
              strokeWidth={2}
              className="cursor-pointer transition-opacity"
              onMouseEnter={() => setHovered(comp)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSelect?.(comp)}
            />
          );
        })}
      </svg>

      {hovered && (
        <div className="absolute top-0 right-0 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs w-56 z-10">
          <p className="font-mono font-medium">{hovered.mpn}</p>
          <p className="text-gray-500">{hovered.manufacturer}</p>
          <p className="mt-1">Risk: <span className="font-bold">{Math.round(hovered.risk_score?.composite_score ?? 0)}</span></p>
          <p className="text-gray-500">{hovered.enrichment?.lifecycle_status ?? 'Unknown'}</p>
        </div>
      )}
    </div>
  );
}
