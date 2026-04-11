import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import TopBar from '../components/layout/TopBar';
import RiskHeatmap from '../components/risk/RiskHeatmap';
import RiskDashboardPanel from '../components/risk/RiskDashboard';
import ComponentCard from '../components/risk/ComponentCard';
import { api } from '../api/client';
import type { Bom, ComponentWithRisk, RiskSummary } from '../types';

export default function RiskAnalysis() {
  const [selectedBomId, setSelectedBomId] = useState<string | null>(null);
  const [selectedComponent, setSelectedComponent] = useState<ComponentWithRisk | null>(null);

  const { data: boms = [] } = useQuery<Bom[]>({ queryKey: ['boms'], queryFn: api.boms.list });

  const activeBomId = selectedBomId || (boms.length > 0 ? boms[0].id : null);

  const { data: componentsData } = useQuery({
    queryKey: ['bom-components', activeBomId],
    queryFn: () => api.boms.components(activeBomId!, { per_page: '200' }),
    enabled: !!activeBomId,
  });

  const { data: summary } = useQuery<RiskSummary>({
    queryKey: ['risk-summary', activeBomId],
    queryFn: () => api.risk.summary(activeBomId!),
    enabled: !!activeBomId,
  });

  const components = componentsData?.items ?? [];
  const withRisk = components.filter((c) => c.risk_score != null);
  const topRisk = [...withRisk].sort((a, b) => (b.risk_score?.composite_score ?? 0) - (a.risk_score?.composite_score ?? 0));

  return (
    <div className="flex flex-col flex-1">
      <TopBar title="Risk Analysis">
        <select
          value={activeBomId ?? ''}
          onChange={(e) => setSelectedBomId(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
        >
          {boms.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>
      </TopBar>

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {!activeBomId ? (
          <p className="text-gray-400">Upload a BOM to see risk analysis.</p>
        ) : (
          <>
            <RiskDashboardPanel summary={summary ?? null} topRiskComponents={topRisk} />

            {withRisk.length > 0 && (
              <div className="bg-white rounded-lg border p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Component Risk Heatmap</h4>
                <RiskHeatmap components={withRisk} onSelect={setSelectedComponent} />
              </div>
            )}
          </>
        )}
      </main>

      {selectedComponent && (
        <ComponentCard component={selectedComponent} onClose={() => setSelectedComponent(null)} />
      )}
    </div>
  );
}
