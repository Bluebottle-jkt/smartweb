'use client';

import { useState } from 'react';
import Link from 'next/link';
import MainLayout from '@/components/MainLayout';
import EntityAutocompleteInput, { EntitySuggestion } from '@/components/EntityAutocompleteInput';
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
  effective_from: string | null;
  effective_to: string | null;
}

interface OwnershipChain {
  taxpayer_id: number;
  taxpayer_name: string;
  npwp: string;
  shareholders: RelEntry[];
  subsidiaries: RelEntry[];
  other_relationships: RelEntry[];
  total_pct_owned: number;
}

export default function StrukturKepemilikanPage() {
  const [selected, setSelected] = useState<EntitySuggestion | null>(null);
  const [data, setData] = useState<OwnershipChain | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelect = async (entity: EntitySuggestion) => {
    setSelected(entity);
    if (!entity.id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await relationshipsApi.ownershipChain(entity.id);
      setData(res.data);
    } catch {
      setError('Gagal memuat struktur kepemilikan.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const pctBadge = (pct: number | null) => {
    if (pct === null || pct === undefined) return null;
    const p = Number(pct);
    const color = p >= 50 ? 'text-red-300 bg-red-900/40' : p >= 25 ? 'text-orange-300 bg-orange-900/40' : 'text-blue-300 bg-blue-900/40';
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-bold ${color}`}>
        {p.toFixed(1)}%
      </span>
    );
  };

  const RelRow = ({ rel, direction }: { rel: RelEntry; direction: 'from' | 'to' }) => {
    const name = direction === 'from' ? rel.from_entity_name : rel.to_entity_name;
    const eType = direction === 'from' ? rel.from_entity_type : rel.to_entity_type;
    const eId = direction === 'from' ? rel.from_entity_id : rel.to_entity_id;
    const path = eType === 'TAXPAYER' ? `/taxpayers/${eId}` : eType === 'BENEFICIAL_OWNER' ? `/beneficial-owners/${eId}` : null;

    return (
      <div className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg hover:bg-gray-800 transition-colors">
        <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center shrink-0 text-xs text-gray-300 font-bold">
          {eType === 'TAXPAYER' ? 'WP' : eType === 'BENEFICIAL_OWNER' ? 'BO' : eType === 'OFFICER' ? 'OF' : '?'}
        </div>
        <div className="flex-1 min-w-0">
          {path ? (
            <Link href={path} className="text-sm font-medium text-blue-300 hover:text-blue-200 truncate block">
              {name}
            </Link>
          ) : (
            <span className="text-sm font-medium text-gray-200 truncate block">{name}</span>
          )}
          <div className="text-xs text-gray-500">{eType}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {pctBadge(rel.pct)}
          {rel.effective_from && (
            <span className="text-xs text-gray-500">{rel.effective_from}</span>
          )}
        </div>
      </div>
    );
  };

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Struktur Kepemilikan</h1>
          <p className="text-gray-400 text-sm mt-1">Visualisasi rantai kepemilikan entitas wajib pajak</p>
        </div>

        {/* Search */}
        <div className="bg-gray-900 rounded-2xl border border-gray-700 p-5 mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Cari Wajib Pajak</label>
          <EntityAutocompleteInput
            placeholder="Ketik nama atau NPWP..."
            entityTypes={['TAXPAYER']}
            onSelect={handleSelect}
          />
        </div>

        {loading && (
          <div className="text-center py-16 text-gray-400">
            <div className="text-4xl animate-spin mb-4">⚙️</div>
            Memuat struktur kepemilikan...
          </div>
        )}

        {error && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-4">{error}</div>
        )}

        {data && !loading && (
          <div className="space-y-6">
            {/* Subject card */}
            <div className="bg-blue-900/30 border border-blue-700 rounded-2xl p-5">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-lg">WP</div>
                <div>
                  <h2 className="text-lg font-bold text-white">{data.taxpayer_name}</h2>
                  <p className="text-sm text-blue-300 font-mono">{data.npwp}</p>
                </div>
                <div className="ml-auto text-right text-sm">
                  <div className="text-gray-400">Total kepemilikan masuk</div>
                  <div className="text-xl font-bold text-orange-300">{data.total_pct_owned.toFixed(1)}%</div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Shareholders */}
              <div className="bg-gray-900 rounded-2xl border border-gray-700 p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-orange-400 inline-block" />
                  Pemegang Saham ({data.shareholders.length})
                </h3>
                {data.shareholders.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-4">Tidak ada pemegang saham tercatat</p>
                ) : (
                  <div className="space-y-2">
                    {data.shareholders.map((rel) => (
                      <RelRow key={rel.id} rel={rel} direction="from" />
                    ))}
                  </div>
                )}
              </div>

              {/* Subsidiaries */}
              <div className="bg-gray-900 rounded-2xl border border-gray-700 p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                  Anak Usaha ({data.subsidiaries.length})
                </h3>
                {data.subsidiaries.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-4">Tidak ada anak usaha tercatat</p>
                ) : (
                  <div className="space-y-2">
                    {data.subsidiaries.map((rel) => (
                      <RelRow key={rel.id} rel={rel} direction="to" />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Other relationships */}
            {data.other_relationships.length > 0 && (
              <div className="bg-gray-900 rounded-2xl border border-gray-700 p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-400 inline-block" />
                  Relasi Lain ({data.other_relationships.length})
                </h3>
                <div className="space-y-2">
                  {data.other_relationships.map((rel) => (
                    <div key={rel.id} className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-gray-500 mb-1">{rel.relationship_type}</div>
                        <div className="flex items-center gap-2 text-sm text-gray-300">
                          <span className="font-medium">{rel.from_entity_name}</span>
                          <span className="text-gray-600">→</span>
                          <span className="font-medium">{rel.to_entity_name}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="text-center">
              <Link
                href={`/network-explorer?npwp=${encodeURIComponent(data.npwp)}`}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-purple-700 hover:bg-purple-600 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Buka di Graph Explorer
              </Link>
            </div>
          </div>
        )}

        {!data && !loading && !error && (
          <div className="text-center py-20 text-gray-500">
            <div className="text-5xl mb-4">🏢</div>
            <p className="text-lg">Pilih wajib pajak untuk melihat struktur kepemilikan</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
