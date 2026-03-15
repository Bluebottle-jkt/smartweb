'use client';

import { useEffect, useState } from 'react';
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
  notes: string | null;
}

export default function KeluargaPemegangSahamPage() {
  const [selected, setSelected] = useState<EntitySuggestion | null>(null);
  const [rels, setRels] = useState<RelEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelect = async (entity: EntitySuggestion) => {
    setSelected(entity);
    if (!entity.id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await relationshipsApi.forEntity('TAXPAYER', entity.id, 'both');
      const all: RelEntry[] = res.data.relationships || [];
      setRels(all.filter((r) => r.relationship_type === 'FAMILY'));
    } catch {
      setError('Gagal memuat data relasi keluarga.');
      setRels([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Keluarga Pemegang Saham</h1>
          <p className="text-gray-400 text-sm mt-1">
            Hubungan keluarga antar pemegang saham dan entitas terkait
          </p>
        </div>

        <div className="bg-gray-900 rounded-2xl border border-gray-700 p-5 mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Pilih Entitas</label>
          <EntityAutocompleteInput
            placeholder="Cari wajib pajak atau beneficial owner..."
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
          <div className="bg-gray-900 rounded-2xl border border-gray-700 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700">
              <span className="text-sm font-semibold text-gray-300">
                Relasi Keluarga — {rels.length} koneksi
              </span>
            </div>

            {rels.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-3xl mb-2">👨‍👩‍👧‍👦</div>
                Tidak ada relasi keluarga yang tercatat
              </div>
            ) : (
              <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                {rels.map((rel) => {
                  const isSubject =
                    rel.from_entity_id === selected.id &&
                    rel.from_entity_type === 'TAXPAYER';
                  const otherName = isSubject ? rel.to_entity_name : rel.from_entity_name;
                  const otherType = isSubject ? rel.to_entity_type : rel.from_entity_type;

                  return (
                    <div
                      key={rel.id}
                      className="bg-gray-800/60 rounded-xl p-4 flex items-center gap-4"
                    >
                      <div className="w-10 h-10 rounded-full bg-pink-900/60 border border-pink-700 flex items-center justify-center text-pink-300 text-sm font-bold shrink-0">
                        {otherType === 'TAXPAYER' ? 'WP' : otherType === 'BENEFICIAL_OWNER' ? 'BO' : 'E'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">{otherName}</div>
                        <div className="text-xs text-gray-400">{otherType}</div>
                        {rel.notes && (
                          <div className="text-xs text-gray-500 mt-0.5 italic">{rel.notes}</div>
                        )}
                      </div>
                      <div className="shrink-0">
                        <span className="px-2 py-1 rounded text-xs bg-pink-900/50 text-pink-300 font-medium">KELUARGA</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {!selected && !loading && (
          <div className="text-center py-20 text-gray-500">
            <div className="text-5xl mb-4">👨‍👩‍👧‍👦</div>
            <p className="text-lg">Pilih entitas untuk melihat jaringan keluarga</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
