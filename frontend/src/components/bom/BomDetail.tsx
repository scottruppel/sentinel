import { useQuery } from '@tanstack/react-query';
import { createColumnHelper } from '@tanstack/react-table';
import DataTable from '../common/DataTable';
import RiskBadge from '../common/Badge';
import { RiskRadar } from '../common/Charts';
import { api } from '../../api/client';
import type { ComponentWithRisk } from '../../types';

const col = createColumnHelper<ComponentWithRisk>();

const columns = [
  col.display({
    id: 'expand',
    header: '',
    cell: ({ row }) => (
      <button onClick={() => row.toggleExpanded()} className="text-gray-400 hover:text-gray-700">
        {row.getIsExpanded() ? '▾' : '▸'}
      </button>
    ),
    size: 30,
  }),
  col.accessor('mpn', { header: 'MPN', cell: (info) => <span className="font-mono text-xs">{info.getValue()}</span> }),
  col.accessor('manufacturer', { header: 'Manufacturer' }),
  col.accessor('reference_designator', { header: 'Ref Des', cell: (info) => <span className="text-xs">{info.getValue()}</span> }),
  col.accessor('quantity', { header: 'Qty', size: 60 }),
  col.accessor('category', { header: 'Category' }),
  col.accessor((row) => row.enrichment?.lifecycle_status, { id: 'lifecycle', header: 'Lifecycle' }),
  col.accessor((row) => row.enrichment?.total_inventory, {
    id: 'inventory',
    header: 'Inventory',
    cell: (info) => {
      const v = info.getValue();
      return v != null ? v.toLocaleString() : '—';
    },
  }),
  col.accessor((row) => row.risk_score?.composite_score ?? null, {
    id: 'risk',
    header: 'Risk',
    cell: (info) => {
      const v = info.getValue();
      return v != null ? <RiskBadge score={v} size="sm" /> : <span className="text-gray-400">—</span>;
    },
  }),
];

function SubComponent({ row }: { row: ComponentWithRisk }) {
  const rs = row.risk_score;
  const en = row.enrichment;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {rs && (
        <div>
          <h4 className="text-sm font-medium mb-2">Risk Breakdown</h4>
          <RiskRadar
            lifecycle={rs.lifecycle_risk}
            supply={rs.supply_risk}
            geographic={rs.geographic_risk}
            supplier={rs.supplier_risk}
            regulatory={rs.regulatory_risk}
            size={200}
          />
        </div>
      )}

      {rs && rs.risk_factors.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2">Risk Factors</h4>
          <ul className="space-y-1 text-xs text-gray-600">
            {rs.risk_factors.map((f, i) => (
              <li key={i} className="flex items-start gap-1">
                <span className="text-risk-critical font-bold">·</span>
                {f.detail}
              </li>
            ))}
          </ul>
          {rs.recommendation && (
            <p className="mt-2 text-xs text-sentinel-700 bg-sentinel-50 p-2 rounded">{rs.recommendation}</p>
          )}
        </div>
      )}

      {en && (
        <div>
          <h4 className="text-sm font-medium mb-2">Enrichment Detail</h4>
          <dl className="grid grid-cols-2 gap-y-1 text-xs">
            <dt className="text-gray-500">Lead Time</dt>
            <dd>{en.avg_lead_time_days ? `${en.avg_lead_time_days} days` : '—'}</dd>
            <dt className="text-gray-500">Distributors</dt>
            <dd>{en.distributor_count ?? '—'}</dd>
            <dt className="text-gray-500">Alternates</dt>
            <dd>{en.num_alternates ?? '—'}</dd>
            <dt className="text-gray-500">Country</dt>
            <dd>{en.country_of_origin ?? '—'}</dd>
            <dt className="text-gray-500">YTEOL</dt>
            <dd>{en.yteol != null ? `${en.yteol}y` : '—'}</dd>
            <dt className="text-gray-500">RoHS</dt>
            <dd>{en.rohs_compliant != null ? (en.rohs_compliant ? 'Yes' : 'No') : '—'}</dd>
          </dl>
        </div>
      )}
    </div>
  );
}

interface BomDetailProps {
  bomId: string;
}

export default function BomDetail({ bomId }: BomDetailProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['bom-components', bomId],
    queryFn: () => api.boms.components(bomId, { per_page: '200' }),
  });

  if (isLoading) return <p className="text-gray-500 p-4">Loading components...</p>;
  if (!data) return null;

  return (
    <DataTable
      data={data.items}
      columns={columns}
      searchPlaceholder="Search components..."
      renderSubComponent={(row) => <SubComponent row={row} />}
    />
  );
}
