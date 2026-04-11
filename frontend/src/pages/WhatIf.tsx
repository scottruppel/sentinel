import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import TopBar from '../components/layout/TopBar';
import ScenarioBuilder from '../components/whatif/ScenarioBuilder';
import ScenarioList from '../components/whatif/ScenarioList';
import ImpactView from '../components/whatif/ImpactView';
import { api } from '../api/client';
import type { Scenario } from '../types';

export default function WhatIf() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showBuilder, setShowBuilder] = useState(false);

  const { data: scenarios = [] } = useQuery<Scenario[]>({
    queryKey: ['scenarios'],
    queryFn: api.scenarios.list,
  });

  return (
    <div className="flex flex-col flex-1">
      <TopBar title="What-If Analysis">
        <button onClick={() => setShowBuilder(!showBuilder)} className="px-4 py-1.5 text-sm bg-sentinel-600 text-white rounded-md hover:bg-sentinel-700">
          {showBuilder ? 'Hide Builder' : 'New Scenario'}
        </button>
      </TopBar>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-64 border-r border-gray-200 bg-white overflow-y-auto p-3">
          <ScenarioList scenarios={scenarios} selectedId={selectedId} onSelect={setSelectedId} />
        </aside>

        <main className="flex-1 overflow-y-auto p-4 space-y-4">
          {showBuilder && (
            <ScenarioBuilder onCreated={() => { setShowBuilder(false); }} />
          )}

          {selectedId ? (
            <ImpactView scenarioId={selectedId} />
          ) : (
            !showBuilder && (
              <div className="flex items-center justify-center h-64 text-gray-400">
                Select a scenario from the sidebar or create a new one
              </div>
            )
          )}
        </main>
      </div>
    </div>
  );
}
