import { useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { Scenario } from '../../types';

interface ScenarioListProps {
  scenarios: Scenario[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const typeLabels: Record<string, string> = {
  country_disruption: 'Country',
  supplier_failure: 'Supplier',
  obsolescence_wave: 'Obsolescence',
  component_removal: 'Removal',
  demand_spike: 'Demand',
};

export default function ScenarioList({ scenarios, selectedId, onSelect }: ScenarioListProps) {
  const queryClient = useQueryClient();

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await api.scenarios.delete(id);
    queryClient.invalidateQueries({ queryKey: ['scenarios'] });
  };

  return (
    <div className="space-y-1">
      {scenarios.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          className={`w-full text-left p-3 rounded-md transition-colors group ${
            selectedId === s.id ? 'bg-sentinel-50 border border-sentinel-200' : 'hover:bg-gray-50 border border-transparent'
          }`}
        >
          <div className="flex items-center justify-between">
            <p className="font-medium text-sm text-gray-900 truncate">{s.name}</p>
            <button
              onClick={(e) => handleDelete(s.id, e)}
              className="text-gray-300 hover:text-risk-critical opacity-0 group-hover:opacity-100 transition-opacity text-xs"
            >
              ✕
            </button>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{typeLabels[s.scenario_type] ?? s.scenario_type}</span>
            <span className={`text-xs ${s.status === 'complete' ? 'text-risk-low' : 'text-gray-400'}`}>{s.status}</span>
          </div>
          {s.summary?.total_components_affected != null && (
            <p className="text-xs text-gray-500 mt-1">{s.summary.total_components_affected} affected</p>
          )}
        </button>
      ))}
      {scenarios.length === 0 && <p className="text-sm text-gray-400 p-3">No scenarios yet</p>}
    </div>
  );
}
