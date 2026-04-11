import { useQuery } from '@tanstack/react-query';
import RiskBadge, { DeltaIndicator } from '../common/Badge';
import { api } from '../../api/client';
import type { ScenarioResult } from '../../types';

interface ImpactViewProps {
  scenarioId: string;
}

export default function ImpactView({ scenarioId }: ImpactViewProps) {
  const { data: result, isLoading } = useQuery<ScenarioResult>({
    queryKey: ['scenario-results', scenarioId],
    queryFn: () => api.scenarios.results(scenarioId),
  });

  if (isLoading) return <p className="text-gray-500">Loading results...</p>;
  if (!result) return null;

  const { summary, baseline_bom_risk, scenario_bom_risk, affected_components, bom_names: bomNamesRaw } = result;
  const bomNames = bomNamesRaw ?? {};

  const labelFor = (bomId: string) => bomNames[bomId] ?? `BOM ${bomId.slice(0, 8)}…`;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <h4 className="text-sm font-medium text-gray-600 mb-3">Baseline</h4>
          {Object.entries(baseline_bom_risk).map(([bomId, score]) => (
            <div key={bomId} className="flex items-center justify-between mb-1 gap-2">
              <span className="text-sm text-gray-700 truncate max-w-[220px]" title={bomId}>
                {labelFor(bomId)}
              </span>
              <RiskBadge score={score} size="sm" />
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg border p-4">
          <h4 className="text-sm font-medium text-gray-600 mb-3">Scenario Impact</h4>
          {Object.entries(scenario_bom_risk).map(([bomId, score]) => {
            const baseline = baseline_bom_risk[bomId] ?? 0;
            return (
              <div key={bomId} className="flex items-center justify-between mb-1 gap-2">
                <span className="text-sm text-gray-700 truncate max-w-[220px]" title={bomId}>
                  {labelFor(bomId)}
                </span>
                <div className="flex items-center gap-2">
                  <RiskBadge score={score} size="sm" />
                  <DeltaIndicator delta={score - baseline} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-5 gap-3">
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-2xl font-bold">{summary.total_components_affected}</p>
          <p className="text-xs text-gray-500">Affected</p>
        </div>
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-2xl font-bold">{summary.boms_affected}</p>
          <p className="text-xs text-gray-500">BOMs</p>
        </div>
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-2xl font-bold text-risk-critical">+{summary.avg_risk_delta.toFixed(1)}</p>
          <p className="text-xs text-gray-500">Avg Delta</p>
        </div>
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-2xl font-bold text-risk-critical">{summary.components_at_critical}</p>
          <p className="text-xs text-gray-500">At Critical</p>
        </div>
        <div className="bg-white rounded-lg border p-3 text-center">
          <p className="text-2xl font-bold">{summary.components_with_no_alternate_source}</p>
          <p className="text-xs text-gray-500">No Alternate</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Affected Components</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left">MPN</th>
                <th className="px-3 py-2 text-left">Manufacturer</th>
                <th className="px-3 py-2 text-left">Baseline</th>
                <th className="px-3 py-2 text-left">Scenario</th>
                <th className="px-3 py-2 text-left">Delta</th>
                <th className="px-3 py-2 text-left">Recommendation</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {affected_components.map((c, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs">{c.mpn}</td>
                  <td className="px-3 py-2">{c.manufacturer}</td>
                  <td className="px-3 py-2"><RiskBadge score={c.baseline_risk} size="sm" /></td>
                  <td className="px-3 py-2"><RiskBadge score={c.scenario_risk} size="sm" /></td>
                  <td className="px-3 py-2"><DeltaIndicator delta={c.delta} /></td>
                  <td className="px-3 py-2 text-xs text-gray-600 max-w-xs truncate">{c.recommendation ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
