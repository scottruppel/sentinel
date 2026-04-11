import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { Bom } from '../../types';

const SCENARIO_TYPES = [
  { value: 'country_disruption', label: 'Country Disruption', fields: ['country', 'severity'] },
  { value: 'supplier_failure', label: 'Supplier Failure', fields: ['manufacturer', 'failure_mode'] },
  { value: 'obsolescence_wave', label: 'Obsolescence Wave', fields: ['target_statuses', 'time_horizon_months'] },
  { value: 'component_removal', label: 'Component Removal', fields: ['mpns', 'reason'] },
  { value: 'demand_spike', label: 'Demand Spike', fields: ['multiplier'] },
];

const SEVERITY_OPTIONS = ['total_loss', 'partial_disruption', 'tariff_increase'];
const FAILURE_MODES = ['bankruptcy', 'exit_product_line', 'force_majeure'];

interface ScenarioBuilderProps {
  onCreated: () => void;
}

export default function ScenarioBuilder({ onCreated }: ScenarioBuilderProps) {
  const [name, setName] = useState('');
  const [description] = useState('');
  const [scenarioType, setScenarioType] = useState('country_disruption');
  const [params, setParams] = useState<Record<string, unknown>>({ country: 'Taiwan', severity: 'total_loss' });
  const [selectedBoms, setSelectedBoms] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: boms = [] } = useQuery<Bom[]>({ queryKey: ['boms'], queryFn: api.boms.list });

  const handleTypeChange = (type: string) => {
    setScenarioType(type);
    if (type === 'country_disruption') setParams({ country: 'Taiwan', severity: 'total_loss' });
    else if (type === 'supplier_failure') setParams({ manufacturer: '', failure_mode: 'bankruptcy' });
    else if (type === 'obsolescence_wave') setParams({ target_statuses: ['NRFND'], time_horizon_months: 12 });
    else if (type === 'component_removal') setParams({ mpns: [], reason: 'obsolete' });
    else if (type === 'demand_spike') setParams({ multiplier: 2.0 });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.scenarios.create({
        name: name || SCENARIO_TYPES.find((t) => t.value === scenarioType)?.label || 'Scenario',
        description: description || undefined,
        scenario_type: scenarioType,
        parameters: params,
        affected_bom_ids: selectedBoms.length > 0 ? selectedBoms : undefined,
      });
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create scenario');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg border p-4 space-y-4">
      <h3 className="font-medium text-gray-800">Create Scenario</h3>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Scenario Type</label>
          <select value={scenarioType} onChange={(e) => handleTypeChange(e.target.value)} className="w-full px-3 py-2 border rounded-md text-sm">
            {SCENARIO_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Auto-generated if empty" className="w-full px-3 py-2 border rounded-md text-sm" />
        </div>
      </div>

      {scenarioType === 'country_disruption' && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Country</label>
            <input type="text" value={String(params.country ?? '')} onChange={(e) => setParams({ ...params, country: e.target.value })} className="w-full px-3 py-2 border rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Severity</label>
            <select value={String(params.severity ?? '')} onChange={(e) => setParams({ ...params, severity: e.target.value })} className="w-full px-3 py-2 border rounded-md text-sm">
              {SEVERITY_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
            </select>
          </div>
        </div>
      )}

      {scenarioType === 'supplier_failure' && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Manufacturer</label>
            <input type="text" value={String(params.manufacturer ?? '')} onChange={(e) => setParams({ ...params, manufacturer: e.target.value })} className="w-full px-3 py-2 border rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Failure Mode</label>
            <select value={String(params.failure_mode ?? '')} onChange={(e) => setParams({ ...params, failure_mode: e.target.value })} className="w-full px-3 py-2 border rounded-md text-sm">
              {FAILURE_MODES.map((m) => <option key={m} value={m}>{m.replace('_', ' ')}</option>)}
            </select>
          </div>
        </div>
      )}

      {scenarioType === 'obsolescence_wave' && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Time Horizon (months)</label>
          <input type="number" value={Number(params.time_horizon_months ?? 12)} onChange={(e) => setParams({ ...params, time_horizon_months: parseInt(e.target.value) })} className="w-32 px-3 py-2 border rounded-md text-sm" />
        </div>
      )}

      {scenarioType === 'component_removal' && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">MPNs (comma-separated)</label>
          <input type="text" value={Array.isArray(params.mpns) ? (params.mpns as string[]).join(', ') : ''} onChange={(e) => setParams({ ...params, mpns: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })} className="w-full px-3 py-2 border rounded-md text-sm" placeholder="XC7Z010-1CLG225C, AD9363BBCZ" />
        </div>
      )}

      {scenarioType === 'demand_spike' && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Multiplier</label>
          <input type="number" step="0.5" value={Number(params.multiplier ?? 2)} onChange={(e) => setParams({ ...params, multiplier: parseFloat(e.target.value) })} className="w-32 px-3 py-2 border rounded-md text-sm" />
        </div>
      )}

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Affected BOMs</label>
        <div className="flex flex-wrap gap-2">
          {boms.map((b) => (
            <label key={b.id} className="flex items-center gap-1 text-sm">
              <input type="checkbox" checked={selectedBoms.includes(b.id)} onChange={(e) => setSelectedBoms(e.target.checked ? [...selectedBoms, b.id] : selectedBoms.filter((id) => id !== b.id))} />
              {b.name}
            </label>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-1">Leave unchecked to apply to all BOMs</p>
      </div>

      {error && <p className="text-sm text-risk-critical">{error}</p>}

      <button type="submit" disabled={submitting} className="px-4 py-2 bg-sentinel-600 text-white rounded-md text-sm hover:bg-sentinel-700 disabled:opacity-50">
        {submitting ? 'Running...' : 'Run Scenario'}
      </button>
    </form>
  );
}
