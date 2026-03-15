'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import MainLayout from '@/components/MainLayout';
import { groupsApi } from '@/lib/api';

interface GroupRow {
  id: number;
  name: string;
  group_code: string;
  member_count?: number;
  risk_score?: number;
  status?: string;
  created_at?: string;
}

export default function GroupKepemilikanPage() {
  const [groups, setGroups] = useState<GroupRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const PAGE_SIZE = 25;

  useEffect(() => {
    setLoading(true);
    setError(null);
    groupsApi
      .list(page, PAGE_SIZE)
      .then((res) => {
        const d = res.data;
        const raw: GroupRow[] = d.groups || d.results || d.items || [];
        const filtered = search
          ? raw.filter((g) => g.name?.toLowerCase().includes(search.toLowerCase()) || g.group_code?.includes(search))
          : raw;
        setGroups(filtered);
        setTotal(d.total || filtered.length);
      })
      .catch(() => setError('Gagal memuat daftar grup.'))
      .finally(() => setLoading(false));
  }, [page, search]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const riskBadge = (score?: number) => {
    if (!score) return null;
    if (score >= 75) return <span className="px-2 py-0.5 rounded text-xs bg-red-900/60 text-red-300">Tinggi</span>;
    if (score >= 50) return <span className="px-2 py-0.5 rounded text-xs bg-orange-900/60 text-orange-300">Sedang</span>;
    return <span className="px-2 py-0.5 rounded text-xs bg-green-900/60 text-green-300">Rendah</span>;
  };

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Group WP</h1>
            <p className="text-gray-400 text-sm mt-1">
              Daftar grup wajib pajak — {total.toLocaleString('id-ID')} grup terdaftar
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="bg-gray-900 rounded-2xl border border-gray-700 p-4 mb-6 flex gap-3">
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput); setPage(1); }}}
            placeholder="Cari nama grup atau kode..."
            className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={() => { setSearch(searchInput); setPage(1); }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium"
          >
            Cari
          </button>
          {search && (
            <button
              onClick={() => { setSearch(''); setSearchInput(''); setPage(1); }}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm"
            >
              Reset
            </button>
          )}
        </div>

        {error && <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-4 mb-6">{error}</div>}

        {loading ? (
          <div className="text-center py-16 text-gray-400">
            <div className="text-4xl animate-spin mb-4">⚙️</div>Memuat data grup...
          </div>
        ) : (
          <div className="bg-gray-900 rounded-2xl border border-gray-700 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700 flex items-center justify-between">
              <span className="text-sm text-gray-400">
                Menampilkan <span className="text-white">{groups.length}</span> grup
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
                    <th className="text-left px-4 py-3">Nama Grup</th>
                    <th className="text-left px-4 py-3">Kode</th>
                    <th className="text-left px-4 py-3">Anggota</th>
                    <th className="text-left px-4 py-3">Status</th>
                    <th className="text-left px-4 py-3">Risiko</th>
                    <th className="text-left px-4 py-3">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-500">Tidak ada grup ditemukan</td></tr>
                  ) : groups.map((g) => (
                    <tr key={g.id} className="border-b border-gray-800 hover:bg-gray-800/40 transition-colors">
                      <td className="px-4 py-3 font-medium text-white">{g.name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-300">{g.group_code}</td>
                      <td className="px-4 py-3 text-gray-300">{g.member_count ?? '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          g.status === 'AKTIF' || !g.status ? 'bg-green-900/50 text-green-300' : 'bg-gray-700 text-gray-300'
                        }`}>
                          {g.status || 'AKTIF'}
                        </span>
                      </td>
                      <td className="px-4 py-3">{riskBadge(g.risk_score)}</td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <Link href={`/groups/${g.id}`} className="text-xs text-blue-400 hover:text-blue-300">Detail</Link>
                          <Link href={`/jaringan-wp?group=${g.id}`} className="text-xs text-purple-400 hover:text-purple-300">Jaringan</Link>
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
