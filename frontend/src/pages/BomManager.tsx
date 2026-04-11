import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import TopBar from '../components/layout/TopBar';
import BomList from '../components/bom/BomList';
import BomDetail from '../components/bom/BomDetail';
import BomUpload from '../components/bom/BomUpload';
import { api } from '../api/client';
import type { Bom } from '../types';

export default function BomManager() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const queryClient = useQueryClient();

  const { data: boms = [] } = useQuery<Bom[]>({ queryKey: ['boms'], queryFn: api.boms.list });

  const { data: enrichStatus } = useQuery({
    queryKey: ['enrichment-status', selectedId],
    queryFn: () => api.enrichment.status(selectedId!),
    enabled: !!selectedId,
  });

  const handleUploaded = () => {
    setShowUpload(false);
    queryClient.invalidateQueries({ queryKey: ['boms'] });
  };

  const handleEnrichAll = async () => {
    if (!selectedId) return;
    await api.enrichment.run(selectedId);
    queryClient.invalidateQueries({ queryKey: ['bom-components', selectedId] });
    queryClient.invalidateQueries({ queryKey: ['enrichment-status', selectedId] });
  };

  const handleScoreAll = async () => {
    if (!selectedId) return;
    await api.risk.score(selectedId);
    queryClient.invalidateQueries({ queryKey: ['bom-components', selectedId] });
    queryClient.invalidateQueries({ queryKey: ['boms'] });
  };

  const handleEnrichAndScore = async () => {
    if (!selectedId) return;
    await api.enrichment.run(selectedId);
    await api.risk.score(selectedId);
    queryClient.invalidateQueries({ queryKey: ['bom-components', selectedId] });
    queryClient.invalidateQueries({ queryKey: ['boms'] });
    queryClient.invalidateQueries({ queryKey: ['enrichment-status', selectedId] });
  };

  return (
    <div className="flex flex-col flex-1">
      <TopBar title="BOM Manager">
        {selectedId && (
          <>
            <button
              onClick={handleEnrichAll}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Enrich All
            </button>
            <button
              onClick={handleScoreAll}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Score All
            </button>
            <button
              onClick={handleEnrichAndScore}
              className="px-3 py-1.5 text-sm bg-sentinel-600 text-white rounded-md hover:bg-sentinel-700"
            >
              Enrich &amp; Score
            </button>
          </>
        )}
        <button
          onClick={() => setShowUpload(true)}
          className="px-4 py-1.5 text-sm bg-sentinel-600 text-white rounded-md hover:bg-sentinel-700"
        >
          Upload BOM
        </button>
      </TopBar>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-64 border-r border-gray-200 bg-white overflow-y-auto p-3">
          <BomList boms={boms} selectedId={selectedId} onSelect={setSelectedId} />
        </aside>

        <main className="flex-1 overflow-y-auto p-4">
          {selectedId && enrichStatus && (
            <div className="mb-4 rounded-md border border-sentinel-200 bg-sentinel-50 px-4 py-2 text-sm text-sentinel-900">
              <span className="font-medium">Enrichment:</span>{' '}
              {enrichStatus.enriched_components}/{enrichStatus.total_components} components enriched ·{' '}
              {enrichStatus.pending_components} pending
            </div>
          )}
          {selectedId ? (
            <BomDetail bomId={selectedId} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              Select a BOM from the sidebar
            </div>
          )}
        </main>
      </div>

      {showUpload && <BomUpload onUploaded={handleUploaded} onClose={() => setShowUpload(false)} />}
    </div>
  );
}
