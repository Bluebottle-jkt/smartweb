'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import MainLayout from '@/components/MainLayout';
import EntityAutocompleteInput, { EntitySuggestion } from '@/components/EntityAutocompleteInput';
import { relationshipsApi } from '@/lib/api';

interface RelEntry {
  id: number;
  from_entity_name: string;
  from_entity_id: number;
  to_entity_name: string;
  to_entity_id: number;
  to_entity_type: string;
  pct: number | null;
  effective_from: string | null;
  effective_to: string | null;
}

export default function AnakUsahaPage() {
  const [selected, setSelected] = useState<EntitySuggestion | null>(null);
  const [subsidiaries, setSubsidiaries] = useState<RelEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelect = async (entity: EntitySuggestion) => {
    setSelected(entity);
    if (!entity.id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await relationshipsApi.forEntity('TAXPAYER', entity.id, 'from');
      const all: RelEntry[] = res.data.relationships || [];
      setSubsidiaries(all.filter((r: any) => r.relationship_type === 'OWNERSHIP'));
    } catch {
      setError('Gagal memuat data anak usaha.');
      setSubsidiaries([]);
    } finally {
      setLoading(false);
    }
  };

  const totalPct = subsidiaries.reduce((s, r) => s + (r.pct ? Number(r.pct) : 0), 0);

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Anak Usaha</h1>
          <p className="text-gray-400 text-sm mt-1">Daftar entitas yang dimiliki oleh wajib pajak tertentu</p>
        </div>

        <div className="bg-gray-900 rounded-2xl border border-gray-700 p-5 mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Wajib Pajak Induk</label>
          <EntityAutocompleteInput
            placeholder="Cari induk perusahaan..."
            entityTypes={['TAXPAYER']}
            onSelect={handleSelect}
          />
        </div>

        {error && <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-4 mb-6">{error}</div>}

        {loading && (
          <div className="text-center py-16 text-gray-400">
            <div className="text-4xl animate-spin mb-4">⚙️</div>Memuat data...
          </div>
        )}

        {selected && !loading && (
          <>
            {/* Summary */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
              {[
                { label: 'Entitas Induk', value: selected.name || selected.npwp_masked },
                { label: 'Jumlah Anak Usaha', value: subsidiaries.length },
                { label: 'Total % Kepemilikan', value: totalPct.toFixed(1) + '%' },
              ].map(({ label, value }) => (
                <div key={label} className="bg-gray-900 rounded-xl border border-gray-700 p-4">
                  <div className="text-xs text-gray-400 mb-1">{label}</div>
                  <div className="text-lg font-bold text-white truncate">{value}</div>
                </div>
              ))}
            </div>

            <div className="bg-gray-900 rounded-2xl border border-gray-700 overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-700">
                <span className="text-sm font-semibold text-gray-300">
                  Anak Usaha — {subsidiaries.length} entitas
                </span>
              </div>

              {subsidiaries.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-3xl mb-2">📭</div>
                  Tidak ada anak usaha yang tercatat untuk entitas ini
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700 text-gray-400 text-xs">
                        <th className="text-left px-4 py-3">Nama Anak Usaha</th>
                        <th className="text-left px-4 py-3">Jenis</th>
                        <th className="text-left px-4 py-3">% Kepemilikan</th>
                        <th className="text-left px-4 py-3">Berlaku Sejak</th>
                        <th className="text-left px-4 py-3">Aksi</th>
                      </tr>
                    </thead>
                    <tbody>
                      {subsidiaries
                        .sort((a, b) => (Number(b.pct) || 0) - (Number(a.pct) || 0))
                        .map((rel) => (
                          <tr key={rel.id} className="border-b border-gray-800 hover:bg-gray-800/40 transition-colors">
                            <td className="px-4 py-3 font-medium text-white">{rel.to_entity_name}</td>
                            <td className="px-4 py-3">
                              <span className="px-2 py-0.5 rounded text-xs bg-gray-700 text-gray-300">{rel.to_entity_type}</span>
                            </td>
                            <td className="px-4 py-3">
                              {rel.pct !== null ? (
                                <div className="flex items-center gap-2">
                                  <div className="w-20 h-1.5 bg-gray-700 rounded-full">
                                    <div
                                      className="h-full bg-emerald-500 rounded-full"
                                      style={{ width: `${Math.min(100, Number(rel.pct))}%` }}
                                    />
                                  </div>
                                  <span className="text-sm font-bold text-emerald-300">{Number(rel.pct).toFixed(1)}%</span>
                                </div>
                              ) : (
                                <span className="text-gray-500">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-gray-400 text-xs">{rel.effective_from || '—'}</td>
                            <td className="px-4 py-3">
                              <div className="flex gap-2">
                                {rel.to_entity_type === 'TAXPAYER' && (
                                  <>
                                    <Link href={`/taxpayers/${rel.to_entity_id}`} className="text-xs text-blue-400 hover:text-blue-300">Detail</Link>
                                    <Link href={`/kepemilikan/struktur`} className="text-xs text-purple-400 hover:text-purple-300">Struktur</Link>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}

        {!selected && !loading && (
          <div className="text-center py-20 text-gray-500">
            <div className="text-5xl mb-4">🏭</div>
            <p className="text-lg">Pilih entitas induk untuk melihat daftar anak usaha</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
