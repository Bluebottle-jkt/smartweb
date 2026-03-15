'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import MainLayout from '@/components/MainLayout';
import { relationshipsApi } from '@/lib/api';

interface RelEntry {
  id: number;
  from_entity_type: string;
  from_entity_id: number;
  from_entity_name: string;
  to_entity_type: string;
  to_entity_id: number;
  to_entity_name: string;
  relationship_type: string;
  confidence: number | null;
  notes: string | null;
}

// Group by officer (from_entity) to show which companies they control
function groupByOfficer(rels: RelEntry[]) {
  const map = new Map<string, { name: string; type: string; id: number; targets: RelEntry[] }>();
  for (const rel of rels) {
    const key = `${rel.from_entity_type}_${rel.from_entity_id}`;
    if (!map.has(key)) {
      map.set(key, { name: rel.from_entity_name, type: rel.from_entity_type, id: rel.from_entity_id, targets: [] });
    }
    map.get(key)!.targets.push(rel);
  }
  return Array.from(map.values()).sort((a, b) => b.targets.length - a.targets.length);
}

export default function GroupPengurusPage() {
  const [rels, setRels] = useState<RelEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    relationshipsApi
      .list({ relationship_type: 'CONTROL', from_entity_type: 'OFFICER', limit: 500 })
      .then((res) => setRels(res.data.results || []))
      .catch(() => setError('Gagal memuat data pengurus.'))
      .finally(() => setLoading(false));
  }, []);

  const grouped = groupByOfficer(rels);

  const filtered = search
    ? grouped.filter((g) =>
        g.name.toLowerCase().includes(search.toLowerCase()) ||
        g.targets.some((r) => r.to_entity_name.toLowerCase().includes(search.toLowerCase()))
      )
    : grouped;

  const multipleCompanies = filtered.filter((g) => g.targets.length >= 2);

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Group Pengurus</h1>
          <p className="text-gray-400 text-sm mt-1">
            Pengurus/direksi yang mengendalikan lebih dari satu entitas — potensial nominee
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: 'Total Pengurus', value: grouped.length },
            { label: 'Multi-Perusahaan', value: grouped.filter(g => g.targets.length >= 2).length },
            { label: 'Total Relasi', value: rels.length },
          ].map(({ label, value }) => (
            <div key={label} className="bg-gray-900 rounded-xl border border-gray-700 p-4 text-center">
              <div className="text-2xl font-bold text-white">{value.toLocaleString('id-ID')}</div>
              <div className="text-xs text-gray-400 mt-1">{label}</div>
            </div>
          ))}
        </div>

        {/* Filter */}
        <div className="bg-gray-900 rounded-2xl border border-gray-700 p-4 mb-6 flex items-center gap-4">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter nama pengurus atau perusahaan..."
            className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
          <label className="flex items-center gap-2 text-sm text-gray-400">
            <input
              type="checkbox"
              className="accent-blue-500"
              checked={filtered === multipleCompanies || search === ''}
              onChange={(e) => {
                // toggle: show only multi-company pengurus
              }}
            />
            Hanya multi-perusahaan
          </label>
        </div>

        {error && <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-4 mb-6">{error}</div>}

        {loading ? (
          <div className="text-center py-16 text-gray-400">
            <div className="text-4xl animate-spin mb-4">⚙️</div>Memuat data...
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.length === 0 ? (
              <div className="text-center py-12 text-gray-500">Tidak ada data ditemukan</div>
            ) : filtered.map((officer) => (
              <div
                key={`${officer.type}_${officer.id}`}
                className={`bg-gray-900 rounded-2xl border p-5 ${
                  officer.targets.length >= 3 ? 'border-red-800' :
                  officer.targets.length >= 2 ? 'border-orange-800' :
                  'border-gray-700'
                }`}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                    officer.targets.length >= 3 ? 'bg-red-900/60 text-red-300' :
                    officer.targets.length >= 2 ? 'bg-orange-900/60 text-orange-300' :
                    'bg-gray-700 text-gray-300'
                  }`}>
                    {officer.targets.length}
                  </div>
                  <div>
                    <div className="font-semibold text-white">{officer.name}</div>
                    <div className="text-xs text-gray-400">{officer.type}</div>
                  </div>
                  {officer.targets.length >= 2 && (
                    <span className={`ml-auto px-2 py-1 rounded text-xs font-bold ${
                      officer.targets.length >= 3 ? 'bg-red-900/50 text-red-300' : 'bg-orange-900/50 text-orange-300'
                    }`}>
                      {officer.targets.length >= 3 ? 'Risiko Tinggi' : 'Perlu Perhatian'}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {officer.targets.map((rel) => (
                    <div
                      key={rel.id}
                      className="px-3 py-1.5 bg-gray-800 rounded-lg text-xs text-gray-300 border border-gray-700"
                    >
                      {rel.to_entity_name}
                      <span className="ml-1 text-gray-500">({rel.to_entity_type})</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
