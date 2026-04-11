import { useQuery } from '@tanstack/react-query';
import TopBar from '../components/layout/TopBar';
import DataTable from '../components/common/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import { api } from '../api/client';
import type { Bom, CrossExposureRow } from '../types';

const col = createColumnHelper<CrossExposureRow>();

export default function CrossExposure() {
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ['cross-exposure'],
    queryFn: api.boms.crossExposure,
  });

  const { data: boms = [] } = useQuery<Bom[]>({ queryKey: ['boms'], queryFn: api.boms.list });
  const idToName = Object.fromEntries(boms.map((b) => [b.id, b.name]));

  const columns = [
    col.accessor('mpn_normalized', {
      header: 'MPN (normalized)',
      cell: (info) => <span className="font-mono text-xs">{info.getValue()}</span>,
    }),
    col.accessor('manufacturer', { header: 'Manufacturer' }),
    col.accessor('bom_count', { header: 'BOMs', size: 70 }),
    col.accessor('total_quantity', {
      header: 'Total qty',
      cell: (info) => (info.getValue() != null ? Number(info.getValue()).toLocaleString() : '—'),
    }),
    col.display({
      id: 'programs',
      header: 'Programs / BOMs',
      cell: ({ row }) => {
        const ids = row.original.bom_ids;
        const names = ids.map((id) => idToName[id] ?? id.slice(0, 8) + '…').join(', ');
        return <span className="text-xs text-gray-600 max-w-md truncate block" title={names}>{names}</span>;
      },
    }),
  ];

  return (
    <div className="flex flex-col flex-1">
      <TopBar title="Cross-BOM exposure" />
      <main className="flex-1 p-6">
        <p className="text-sm text-gray-600 mb-4 max-w-3xl">
          Parts that appear on more than one BOM (normalized MPN + manufacturer). Shared components drive portfolio-level
          concentration risk.
        </p>
        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="text-gray-500">No overlapping parts across BOMs. Upload multiple BOMs with shared MPNs to see exposure.</p>
        ) : (
          <DataTable data={rows} columns={columns} />
        )}
      </main>
    </div>
  );
}
