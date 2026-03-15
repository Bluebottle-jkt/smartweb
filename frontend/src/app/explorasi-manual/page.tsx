'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import MainLayout from '@/components/MainLayout';
import { taxpayersApi, beneficialOwnersApi } from '@/lib/api';

type EntityKind = 'taxpayer' | 'beneficial_owner';

interface TaxpayerRow {
  id: number;
  name: string;
  npwp_masked: string;
  entity_type: string;
  status: string;
  city: string;
  kpp_name: string;
  risk_score: number | null;
}

interface BORow {
  id: number;
  name: string;
  nationality: string;
  id_number: string;
  domicile_country: string;
}

const ENTITY_TYPE_OPTIONS = ['', 'PT', 'CV', 'FIRMA', 'YAYASAN', 'KOPERASI', 'ORANG_PRIBADI'];
const STATUS_OPTIONS = ['', 'AKTIF', 'NON_AKTIF', 'CABANG'];

export default function ExplorasiManualPage() {
  const [kind, setKind] = useState<EntityKind>('taxpayer');

  // Taxpayer filters
  const [search, setSearch] = useState('');
  const [entityType, setEntityType] = useState('');
  const [status, setStatus] = useState('');

  // BO filters
  const [boSearch, setBoSearch] = useState('');
  const [nationality, setNationality] = useState('');

  // Results
  const [taxpayers, setTaxpayers] = useState<TaxpayerRow[]>([]);
  const [bos, setBos] = useState<BORow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const PAGE_SIZE = 20;

  const doSearch = useCallback(async (p = 1) => {
    setLoading(true);
    setError(null);
    setPage(p);
    try {
      if (kind === 'taxpayer') {
        const res = await taxpayersApi.list(p, PAGE_SIZE, search || undefined, entityType || undefined, status || undefined);
        const d = res.data;
        setTaxpayers(d.taxpayers || d.results || []);
        setTotal(d.total || 0);
      } else {
        const res = await beneficialOwnersApi.list(p, PAGE_SIZE, boSearch || undefined, nationality || undefined);
        const d = res.data;
        setBos(d.beneficial_owners || d.results || []);
        setTotal(d.total || 0);
      }
      setSearched(true);
    } catch {
      setError('Gagal memuat data. Pastikan server berjalan.');
    } finally {
      setLoading(false);
    }
  }, [kind, search, entityType, status, boSearch, nationality]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const riskBadge = (score: number | null) => {
    if (score === null || score === undefined) return null;
    const s = Number(score);
    if (s >= 75) return <span className="px-2 py-0.5 rounded text-xs bg-red-900/60 text-red-300 font-semibold">Tinggi</span>;
    if (s >= 50) return <span className="px-2 py-0.5 rounded text-xs bg-orange-900/60 text-orange-300 font-semibold">Sedang</span>;
    return <span className="px-2 py-0.5 rounded text-xs bg-green-900/60 text-green-300 font-semibold">Rendah</span>;
  };

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            Eksplorasi Manual
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Jelajahi entitas wajib pajak dengan filter multi-dimensi
          </p>
        </div>

        {/* Kind selector */}
        <div className="flex gap-2 mb-6">
          {(['taxpayer', 'beneficial_owner'] as EntityKind[]).map((k) => (
            <button
              key={k}
              onClick={() => { setKind(k); setSearched(false); setTaxpayers([]); setBos([]); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                kind === k
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {k === 'taxpayer' ? 'Wajib Pajak' : 'Beneficial Owner'}
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="bg-gray-900 rounded-2xl border border-gray-700 p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Filter Pencarian</h2>

          {kind === 'taxpayer' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Nama / NPWP</label>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && doSearch(1)}
                  placeholder="Cari nama atau NPWP..."
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Jenis Entitas</label>
                <select
                  value={entityType}
                  onChange={(e) => setEntityType(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  {ENTITY_TYPE_OPTIONS.map((o) => (
                    <option key={o} value={o}>{o || '— Semua Jenis —'}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Status</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o} value={o}>{o || '— Semua Status —'}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={() => doSearch(1)}
                  disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                >
                  {loading ? 'Mencari...' : 'Cari'}
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Nama</label>
                <input
                  value={boSearch}
                  onChange={(e) => setBoSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && doSearch(1)}
                  placeholder="Cari nama BO..."
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Kewarganegaraan</label>
                <input
                  value={nationality}
                  onChange={(e) => setNationality(e.target.value)}
                  placeholder="mis. ID, SG, CN..."
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={() => doSearch(1)}
                  disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                >
                  {loading ? 'Mencari...' : 'Cari'}
                </button>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-4 mb-6">{error}</div>
        )}

        {/* Results */}
        {searched && (
          <div className="bg-gray-900 rounded-2xl border border-gray-700 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700 flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-300">
                Hasil: <span className="text-white">{total.toLocaleString('id-ID')}</span> entitas
              </span>
              {totalPages > 1 && (
                <div className="flex items-center gap-2 text-sm">
                  <button
                    onClick={() => doSearch(page - 1)}
                    disabled={page <= 1 || loading}
                    className="px-3 py-1 rounded bg-gray-800 text-gray-300 disabled:opacity-40 hover:bg-gray-700"
                  >
                    ‹
                  </button>
                  <span className="text-gray-400">{page} / {totalPages}</span>
                  <button
                    onClick={() => doSearch(page + 1)}
                    disabled={page >= totalPages || loading}
                    className="px-3 py-1 rounded bg-gray-800 text-gray-300 disabled:opacity-40 hover:bg-gray-700"
                  >
                    ›
                  </button>
                </div>
              )}
            </div>

            {kind === 'taxpayer' ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 text-gray-400 text-xs">
                      <th className="text-left px-4 py-3">Nama</th>
                      <th className="text-left px-4 py-3">NPWP</th>
                      <th className="text-left px-4 py-3">Jenis</th>
                      <th className="text-left px-4 py-3">Status</th>
                      <th className="text-left px-4 py-3">Kota / KPP</th>
                      <th className="text-left px-4 py-3">Risiko</th>
                      <th className="text-left px-4 py-3">Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {taxpayers.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-8 text-gray-500">
                          Tidak ada data ditemukan
                        </td>
                      </tr>
                    ) : taxpayers.map((tp) => (
                      <tr key={tp.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                        <td className="px-4 py-3 font-medium text-white">{tp.name}</td>
                        <td className="px-4 py-3 text-gray-300 font-mono text-xs">{tp.npwp_masked}</td>
                        <td className="px-4 py-3 text-gray-400">{tp.entity_type}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            tp.status === 'AKTIF' ? 'bg-green-900/50 text-green-300' :
                            tp.status === 'NON_AKTIF' ? 'bg-red-900/50 text-red-300' :
                            'bg-gray-700 text-gray-300'
                          }`}>
                            {tp.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-400 text-xs">
                          <div>{tp.city}</div>
                          <div className="text-gray-500">{tp.kpp_name}</div>
                        </td>
                        <td className="px-4 py-3">{riskBadge(tp.risk_score)}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <Link
                              href={`/taxpayers/${tp.id}`}
                              className="text-xs text-blue-400 hover:text-blue-300"
                            >
                              Detail
                            </Link>
                            <Link
                              href={`/network-explorer?npwp=${encodeURIComponent(tp.npwp_masked)}`}
                              className="text-xs text-purple-400 hover:text-purple-300"
                            >
                              Graf
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 text-gray-400 text-xs">
                      <th className="text-left px-4 py-3">Nama</th>
                      <th className="text-left px-4 py-3">No. Identitas</th>
                      <th className="text-left px-4 py-3">Kewarganegaraan</th>
                      <th className="text-left px-4 py-3">Negara Domisili</th>
                      <th className="text-left px-4 py-3">Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bos.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="text-center py-8 text-gray-500">
                          Tidak ada data ditemukan
                        </td>
                      </tr>
                    ) : bos.map((bo) => (
                      <tr key={bo.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                        <td className="px-4 py-3 font-medium text-white">{bo.name}</td>
                        <td className="px-4 py-3 text-gray-300 font-mono text-xs">{bo.id_number}</td>
                        <td className="px-4 py-3 text-gray-400">{bo.nationality}</td>
                        <td className="px-4 py-3 text-gray-400">{bo.domicile_country}</td>
                        <td className="px-4 py-3">
                          <Link
                            href={`/beneficial-owners/${bo.id}`}
                            className="text-xs text-blue-400 hover:text-blue-300"
                          >
                            Detail
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {!searched && !loading && (
          <div className="text-center py-20 text-gray-500">
            <div className="text-5xl mb-4">🔍</div>
            <p className="text-lg">Masukkan kriteria filter dan tekan Cari</p>
            <p className="text-sm mt-2 text-gray-600">Kosongkan semua filter untuk melihat semua entitas</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
