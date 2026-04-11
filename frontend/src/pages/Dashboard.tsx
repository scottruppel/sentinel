import { useQuery } from '@tanstack/react-query';
import TopBar from '../components/layout/TopBar';
import RiskBadge from '../components/common/Badge';
import { api } from '../api/client';
import type { Bom, Scenario } from '../types';
import { Link } from 'react-router-dom';

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const { data: boms = [], isLoading } = useQuery<Bom[]>({ queryKey: ['boms'], queryFn: api.boms.list });
  const { data: scenarios = [] } = useQuery<Scenario[]>({ queryKey: ['scenarios'], queryFn: api.scenarios.list });

  const { data: enrichCoverage } = useQuery({
    queryKey: ['dashboard-enrich', boms.map((b) => b.id).join(',')],
    queryFn: async (): Promise<{ enriched: number; total: number }> => {
      const rows = await Promise.all(
        boms.map(async (b) => {
          try {
            return await api.enrichment.status(b.id);
          } catch {
            return { total_components: 0, enriched_components: 0, pending_components: 0 };
          }
        }),
      );
      const enriched = rows.reduce((a, s) => a + s.enriched_components, 0);
      const total = rows.reduce((a, s) => a + s.total_components, 0);
      return { enriched, total };
    },
    enabled: boms.length > 0,
  });

  const totalComponents = boms.reduce((sum, b) => sum + b.component_count, 0);
  const scored = boms.filter((b) => b.risk_score_overall != null);
  const avgRisk =
    scored.reduce((sum, b) => sum + (b.risk_score_overall ?? 0), 0) / Math.max(scored.length, 1);
  const completedScenarios = scenarios.filter((s) => s.status === 'complete').length;

  return (
    <div className="flex flex-col flex-1">
      <TopBar title="Dashboard">
        <Link
          to="/boms"
          className="px-4 py-2 bg-sentinel-600 text-white rounded-md text-sm hover:bg-sentinel-700 transition-colors"
        >
          Upload BOM
        </Link>
      </TopBar>
      <main className="flex-1 p-6 space-y-6">
        {isLoading ? (
          <p className="text-gray-500">Loading...</p>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <StatCard label="Total BOMs" value={boms.length} />
              <StatCard label="Components Tracked" value={totalComponents} />
              <StatCard
                label="Enrichment coverage"
                value={
                  boms.length === 0
                    ? '—'
                    : enrichCoverage
                      ? `${enrichCoverage.enriched}/${enrichCoverage.total}`
                      : '…'
                }
                sub="components with enrichment rows"
              />
              <StatCard label="Average Risk Score" value={Math.round(avgRisk || 0)} sub="across scored BOMs" />
              <StatCard label="Active Scenarios" value={completedScenarios} sub="completed what-if runs" />
            </div>

            {boms.length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-5">
                <h3 className="text-sm font-medium text-gray-700 mb-4">Uploaded BOMs</h3>
                <div className="space-y-3">
                  {boms.map((bom) => (
                    <div key={bom.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                      <div>
                        <p className="font-medium text-gray-900">{bom.name}</p>
                        <p className="text-xs text-gray-500">
                          {bom.component_count} components · {bom.program || 'No program'}
                        </p>
                      </div>
                      {bom.risk_score_overall != null && <RiskBadge score={bom.risk_score_overall} />}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {boms.length === 0 && (
              <div className="text-center py-16">
                <p className="text-gray-400 text-lg">No BOMs uploaded yet</p>
                <Link
                  to="/boms"
                  className="mt-4 inline-block px-4 py-2 bg-sentinel-600 text-white rounded-md text-sm hover:bg-sentinel-700"
                >
                  Upload your first BOM
                </Link>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
