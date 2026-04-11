import RiskBadge from '../common/Badge';
import { RiskDistribution } from '../common/Charts';
import type { RiskSummary, ComponentWithRisk } from '../../types';

interface RiskDashboardProps {
  summary: RiskSummary | null;
  topRiskComponents?: ComponentWithRisk[];
}

export default function RiskDashboard({ summary, topRiskComponents }: RiskDashboardProps) {
  if (!summary) return <p className="text-gray-400">No risk data available. Run risk scoring first.</p>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Overall Score</p>
          <p className="text-2xl font-bold">{Math.round(summary.overall_score)}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Critical</p>
          <p className="text-2xl font-bold text-risk-critical">{summary.critical_count}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">High</p>
          <p className="text-2xl font-bold text-risk-high">{summary.high_count}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Medium</p>
          <p className="text-2xl font-bold text-risk-medium">{summary.medium_count}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">Low</p>
          <p className="text-2xl font-bold text-risk-low">{summary.low_count}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Risk Distribution</h4>
        <RiskDistribution
          critical={summary.critical_count}
          high={summary.high_count}
          medium={summary.medium_count}
          low={summary.low_count}
        />
      </div>

      {topRiskComponents && topRiskComponents.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Top 10 At-Risk Components</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">MPN</th>
                  <th className="px-3 py-2 text-left">Manufacturer</th>
                  <th className="px-3 py-2 text-left">Lifecycle</th>
                  <th className="px-3 py-2 text-left">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {topRiskComponents.slice(0, 10).map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-mono text-xs">{c.mpn}</td>
                    <td className="px-3 py-2">{c.manufacturer}</td>
                    <td className="px-3 py-2 text-xs">{c.enrichment?.lifecycle_status ?? '—'}</td>
                    <td className="px-3 py-2">
                      {c.risk_score && <RiskBadge score={c.risk_score.composite_score} size="sm" />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
