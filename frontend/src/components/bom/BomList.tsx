import RiskBadge from '../common/Badge';
import type { Bom } from '../../types';

interface BomListProps {
  boms: Bom[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function BomList({ boms, selectedId, onSelect }: BomListProps) {
  return (
    <div className="space-y-1">
      {boms.map((bom) => (
        <button
          key={bom.id}
          onClick={() => onSelect(bom.id)}
          className={`w-full text-left p-3 rounded-md transition-colors ${
            selectedId === bom.id ? 'bg-sentinel-50 border border-sentinel-200' : 'hover:bg-gray-50 border border-transparent'
          }`}
        >
          <p className="font-medium text-sm text-gray-900 truncate">{bom.name}</p>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-gray-500">{bom.component_count} parts</span>
            {bom.risk_score_overall != null && <RiskBadge score={bom.risk_score_overall} size="sm" />}
          </div>
        </button>
      ))}
      {boms.length === 0 && <p className="text-sm text-gray-400 p-3">No BOMs uploaded</p>}
    </div>
  );
}
