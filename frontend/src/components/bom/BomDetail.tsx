import { useMutation, useQuery } from '@tanstack/react-query';
import { createColumnHelper } from '@tanstack/react-table';
import { useState } from 'react';
import DataTable from '../common/DataTable';
import RiskBadge from '../common/Badge';
import { RiskRadar } from '../common/Charts';
import { api } from '../../api/client';
import type { ComponentWithRisk, NarrativeResponse } from '../../types';

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
  const { data: intelSettings } = useQuery({
    queryKey: ['intelligence-settings'],
    queryFn: () => api.intelligence.settings(),
  });
  const [useLlm, setUseLlm] = useState(true);
  const [allowRemoteLlm, setAllowRemoteLlm] = useState(false);
  const [narrative, setNarrative] = useState<NarrativeResponse | null>(null);

  const narrativeMut = useMutation({
    mutationFn: () =>
      api.intelligence.narrative(row.id, {
        use_llm: useLlm && !!intelSettings?.llm_enabled,
        allow_remote_llm: allowRemoteLlm,
      }),
    onSuccess: (data) => setNarrative(data),
  });

  return (
    <div className="space-y-6">
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

      <div className="border border-sentinel-200 rounded-lg p-4 bg-white">
        <h4 className="text-sm font-medium mb-2">Intelligence analysis</h4>
        <p className="text-xs text-gray-500 mb-3">
          Tier B context (scores, MPN) is packaged locally; optional LLM uses OpenAI-compatible endpoint. Tier C
          public headlines match your regions/keywords. Policy {intelSettings?.policy_version ?? '—'}.
        </p>
        <div className="flex flex-wrap gap-4 items-center mb-3 text-xs">
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              checked={useLlm && !!intelSettings?.llm_enabled}
              disabled={!intelSettings?.llm_enabled}
              onChange={(e) => setUseLlm(e.target.checked)}
            />
            Use LLM (requires LLM_ENABLED)
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              checked={allowRemoteLlm}
              onChange={(e) => setAllowRemoteLlm(e.target.checked)}
            />
            Allow non-localhost LLM
          </label>
          {!intelSettings?.llm_enabled && (
            <span className="text-amber-700">LLM disabled — analysis uses rules + public matches only.</span>
          )}
        </div>
        <button
          type="button"
          onClick={() => narrativeMut.mutate()}
          disabled={narrativeMut.isPending}
          className="text-xs px-3 py-1.5 bg-sentinel-700 text-white rounded hover:bg-sentinel-800 disabled:opacity-50"
        >
          {narrativeMut.isPending ? 'Running…' : 'Run analysis'}
        </button>
        {narrativeMut.isError && (
          <p className="text-xs text-red-600 mt-2">{(narrativeMut.error as Error).message}</p>
        )}
        {narrative && (
          <div className="mt-4 space-y-3 text-xs">
            <p className="text-gray-600">
              Source: <strong>{narrative.source}</strong>
              {narrative.remote_llm_used ? ' · remote LLM' : ''} · policy {narrative.policy_version}
            </p>
            {narrative.raw_model_error && (
              <p className="text-amber-800 bg-amber-50 p-2 rounded">LLM fallback: {narrative.raw_model_error}</p>
            )}
            <div>
              <h5 className="font-medium text-gray-800">Facts</h5>
              <ul className="list-disc pl-4 text-gray-600">
                {narrative.analysis.facts_used.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
            <div>
              <h5 className="font-medium text-gray-800">Interpretation</h5>
              <p className="text-gray-600">{narrative.analysis.interpretation}</p>
            </div>
            <div>
              <h5 className="font-medium text-gray-800">Portfolio impact</h5>
              <p className="text-gray-600">{narrative.analysis.portfolio_impact}</p>
            </div>
            <div>
              <h5 className="font-medium text-gray-800">Actions</h5>
              <ul className="list-disc pl-4 text-gray-600">
                {narrative.analysis.actions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
            {narrative.analysis.citations.length > 0 && (
              <div>
                <h5 className="font-medium text-gray-800">Citations</h5>
                <ul className="space-y-1">
                  {narrative.analysis.citations.map((c, i) => (
                    <li key={i}>
                      <a href={c.source_url} target="_blank" rel="noreferrer" className="text-sentinel-700 underline">
                        {c.title || c.source_url}
                      </a>
                      {c.relevance && <span className="text-gray-500"> — {c.relevance}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {narrative.matched_events.length > 0 && (
              <div>
                <h5 className="font-medium text-gray-800">Matched market events</h5>
                <ul className="space-y-1 text-gray-600">
                  {narrative.matched_events.map((e) => (
                    <li key={e.id}>
                      <a href={e.source_url} className="text-sentinel-700 underline" target="_blank" rel="noreferrer">
                        {e.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
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
