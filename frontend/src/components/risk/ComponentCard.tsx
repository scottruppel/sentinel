import RiskBadge from '../common/Badge';
import { RiskRadar } from '../common/Charts';
import type { ComponentWithRisk } from '../../types';

interface ComponentCardProps {
  component: ComponentWithRisk;
  onClose: () => void;
}

export default function ComponentCard({ component, onClose }: ComponentCardProps) {
  const rs = component.risk_score;
  const en = component.enrichment;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h3 className="font-mono font-semibold">{component.mpn}</h3>
            <p className="text-sm text-gray-500">{component.manufacturer}</p>
          </div>
          <div className="flex items-center gap-3">
            {rs && <RiskBadge score={rs.composite_score} />}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {rs && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm font-medium mb-2">Risk Radar</h4>
                <RiskRadar
                  lifecycle={rs.lifecycle_risk}
                  supply={rs.supply_risk}
                  geographic={rs.geographic_risk}
                  supplier={rs.supplier_risk}
                  regulatory={rs.regulatory_risk}
                />
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Risk Factors</h4>
                <ul className="space-y-2 text-sm">
                  {rs.risk_factors.map((f, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-xs bg-gray-100 rounded px-1.5 py-0.5 shrink-0">{f.contribution}</span>
                      <span className="text-gray-700">{f.detail}</span>
                    </li>
                  ))}
                </ul>
                {rs.recommendation && (
                  <div className="mt-3 p-3 bg-sentinel-50 rounded-md text-sm text-sentinel-700">
                    <p className="font-medium text-xs mb-1">Recommendation</p>
                    {rs.recommendation}
                  </div>
                )}
              </div>
            </div>
          )}

          {en && (
            <div>
              <h4 className="text-sm font-medium mb-2">Enrichment Data</h4>
              <dl className="grid grid-cols-3 gap-y-2 text-sm">
                <div><dt className="text-gray-500 text-xs">Lifecycle</dt><dd>{en.lifecycle_status ?? '—'}</dd></div>
                <div><dt className="text-gray-500 text-xs">YTEOL</dt><dd>{en.yteol != null ? `${en.yteol}y` : '—'}</dd></div>
                <div><dt className="text-gray-500 text-xs">Inventory</dt><dd>{en.total_inventory?.toLocaleString() ?? '—'}</dd></div>
                <div><dt className="text-gray-500 text-xs">Lead Time</dt><dd>{en.avg_lead_time_days ? `${en.avg_lead_time_days}d` : '—'}</dd></div>
                <div><dt className="text-gray-500 text-xs">Distributors</dt><dd>{en.distributor_count ?? '—'}</dd></div>
                <div><dt className="text-gray-500 text-xs">Alternates</dt><dd>{en.num_alternates ?? '—'}</dd></div>
                <div><dt className="text-gray-500 text-xs">Country</dt><dd>{en.country_of_origin ?? '—'}</dd></div>
                <div><dt className="text-gray-500 text-xs">Single Source</dt><dd>{en.single_source != null ? (en.single_source ? 'Yes' : 'No') : '—'}</dd></div>
                <div><dt className="text-gray-500 text-xs">RoHS</dt><dd>{en.rohs_compliant != null ? (en.rohs_compliant ? 'Yes' : 'No') : '—'}</dd></div>
              </dl>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
