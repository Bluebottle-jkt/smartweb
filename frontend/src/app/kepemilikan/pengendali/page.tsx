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
  pct: number | null;
  confidence: number | null;
}

export default function PengendaliPage() {
  const [data, setData] = useState<RelEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const PAGE_SIZE = 30;

  useEffect(() => {
    setLoading(true);
    setError(null);
    relationshipsApi
      .list({ relationship_type: 'CONTROL', skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE })
      .then((res) => {
        setData(res.data.results || []);
        setTotal(res.data.total || 0);
      })
      .catch(() => setError('Gagal memuat data pengendali.'))
      .finally(() => setLoading(false));
  }, [page]);

  const filtered = search
    ? data.filter((r) =>
        r.from_entity_name.toLowerCase().includes(search.toLowerCase()) ||
        r.to_entity_name.toLowerCase().includes(search.toLowerCase())
      )
    : data;

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Pengendali</h1>
            <p className="text-gray-400 text-sm mt-1">
              Daftar hubungan pengendalian antar entitas — total {total.toLocaleString('id-ID')} relasi
            </p>
          </div>
        </div>

        {/* Filter */}
        <div className="bg-gray-900 rounded-2xl border border-gray-700 p-4 mb-6">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter nama pengendali atau entitas..."
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        {error && <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-4 mb-6">{error}</div>}

        {loading ? (
          <div className="text-center py-16 text-gray-400">
            <div className="text-4xl animate-spin mb-4">⚙️</div>Memuat data...
          </div>
        ) : (
          <div className="bg-gray-900 rounded-2xl border border-gray-700 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700 flex items-center justify-between">
              <span className="text-sm text-gray-400">
                Menampilkan <span className="text-white font-medium">{filtered.length}</span> relasi
              </span>
              {totalPages > 1 && (
                <div className="flex items-center gap-2 text-sm">
                  <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                    className="px-3 py-1 rounded bg-gray-800 text-gray-300 disabled:opacity-40">‹</button>
                  <span className="text-gray-400">{page} / {totalPages}</span>
                  <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                    className="px-3 py-1 rounded bg-gray-800 text-gray-300 disabled:opacity-40">›</button>
                </div>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400 text-xs">
                    <th className="text-left px-4 py-3">Pengendali</th>
                    <th className="text-left px-4 py-3">Jenis</th>
                    <th className="text-left px-4 py-3">Entitas Dikendalikan</th>
                    <th className="text-left px-4 py-3">Jenis</th>
                    <th className="text-left px-4 py-3">Keyakinan</th>
                    <th className="text-left px-4 py-3">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-500">Tidak ada data</td></tr>
                  ) : filtered.map((rel) => (
                    <tr key={rel.id} className="border-b border-gray-800 hover:bg-gray-800/40 transition-colors">
                      <td className="px-4 py-3 font-medium text-white">{rel.from_entity_name}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded text-xs bg-gray-700 text-gray-300">{rel.from_entity_type}</span>
                      </td>
                      <td className="px-4 py-3 text-gray-300">{rel.to_entity_name}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded text-xs bg-gray-700 text-gray-300">{rel.to_entity_type}</span>
                      </td>
                      <td className="px-4 py-3">
                        {rel.confidence !== null && (
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-gray-700 rounded-full">
                              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(Number(rel.confidence) * 100).toFixed(0)}%` }} />
                            </div>
                            <span className="text-xs text-gray-400">{(Number(rel.confidence) * 100).toFixed(0)}%</span>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          {rel.to_entity_type === 'TAXPAYER' && (
                            <Link href={`/kepemilikan/struktur?id=${rel.to_entity_id}`} className="text-xs text-blue-400 hover:text-blue-300">
                              Struktur
                            </Link>
                          )}
                          {rel.from_entity_type === 'TAXPAYER' && (
                            <Link href={`/network-explorer?npwp=${rel.from_entity_id}`} className="text-xs text-purple-400 hover:text-purple-300">
                              Graf
                            </Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
