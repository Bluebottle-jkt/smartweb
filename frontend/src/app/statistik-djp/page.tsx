'use client';

import { useEffect, useState } from 'react';
import MainLayout from '@/components/MainLayout';
import { statisticsApi } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type NationalStat = {
  total_taxpayers: number;
  total_groups: number;
  total_bos: number;
  total_officers: number;
  total_relationships: number;
  total_kanwil: number;
  total_kpp: number;
  total_detections: number;
};

type KanwilStat = {
  kanwil_id: number;
  kanwil_name: string;
  kanwil_code: string;
  taxpayer_count: number;
  group_count: number;
  bo_count: number;
  officer_count: number;
  relationship_count: number;
  kpp_count: number;
  detection_count: number;
  shell_candidate_count: number;
  nominee_candidate_count: number;
  vat_carousel_count: number;
};

type KPPStat = {
  kpp_id: number;
  kpp_name: string;
  kpp_code: string;
  city_name?: string;
  taxpayer_count: number;
  group_count: number;
  bo_count: number;
  detection_count: number;
};

// ---------------------------------------------------------------------------
// NationalCard
// ---------------------------------------------------------------------------
function NationalCard({ label, value, icon, color }: {
  label: string; value: number; icon: string; color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 flex items-center gap-4">
      <div className={`text-2xl w-12 h-12 flex items-center justify-center rounded-lg ${color}`}>
        {icon}
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value.toLocaleString('id-ID')}</div>
        <div className="text-xs text-gray-400">{label}</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MiniBar
// ---------------------------------------------------------------------------
function MiniBar({ value, max }: { value: number; max: number }) {
  const pct = Math.round((value / Math.max(max, 1)) * 100);
  return (
    <div className="h-1 bg-gray-700 rounded-full overflow-hidden w-full mt-1">
      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function StatistikDjpPage() {
  const [national, setNational] = useState<NationalStat | null>(null);
  const [kanwilList, setKanwilList] = useState<KanwilStat[]>([]);
  const [kppList, setKppList] = useState<KPPStat[]>([]);
  const [selectedKanwil, setSelectedKanwil] = useState<KanwilStat | null>(null);
  const [year, setYear] = useState<number>(new Date().getFullYear() - 1);
  const [loading, setLoading] = useState(true);
  const [kppLoading, setKppLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load national + kanwil on mount / year change
  useEffect(() => {
    setLoading(true);
    setError(null);
    setSelectedKanwil(null);
    setKppList([]);
    Promise.all([
      statisticsApi.national(year),
      statisticsApi.kanwil(year),
    ])
      .then(([natRes, kwRes]) => {
        setNational(natRes.data);
        setKanwilList(kwRes.data);
      })
      .catch(() => setError('Gagal memuat statistik. Pastikan server berjalan.'))
      .finally(() => setLoading(false));
  }, [year]);

  // Load KPP when kanwil selected
  const handleKanwilClick = (kw: KanwilStat) => {
    if (selectedKanwil?.kanwil_id === kw.kanwil_id) {
      setSelectedKanwil(null);
      setKppList([]);
      return;
    }
    setSelectedKanwil(kw);
    setKppLoading(true);
    statisticsApi
      .kpp(kw.kanwil_id, year)
      .then((res) => setKppList(res.data))
      .catch(() => setKppList([]))
      .finally(() => setKppLoading(false));
  };

  const yearOptions = Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i);
  const maxTp = Math.max(...kanwilList.map((k) => k.taxpayer_count), 1);

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              📊 Statistik DJP
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Dashboard statistik Kanwil dan KPP Direktorat Jenderal Pajak
            </p>
          </div>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-600 focus:outline-none focus:border-blue-500"
          >
            {yearOptions.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {loading && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center text-gray-400">
              <div className="text-4xl animate-spin mb-4">⚙️</div>
              <div>Memuat statistik…</div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-4 mb-6">
            {error}
          </div>
        )}

        {!loading && !error && national && (
          <>
            {/* National overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <NationalCard label="Wajib Pajak" value={national.total_taxpayers} icon="🏢" color="bg-blue-900" />
              <NationalCard label="Grup WP" value={national.total_groups} icon="🏛️" color="bg-purple-900" />
              <NationalCard label="Beneficial Owner" value={national.total_bos} icon="👤" color="bg-emerald-900" />
              <NationalCard label="Pejabat / Officer" value={national.total_officers} icon="💼" color="bg-amber-900" />
              <NationalCard label="Relasi / Hubungan" value={national.total_relationships} icon="🔗" color="bg-cyan-900" />
              <NationalCard label="Total Kanwil" value={national.total_kanwil} icon="🏢" color="bg-indigo-900" />
              <NationalCard label="Total KPP" value={national.total_kpp} icon="🏬" color="bg-teal-900" />
              <NationalCard label="Deteksi Risiko" value={national.total_detections} icon="🚨" color="bg-red-900" />
            </div>

            {/* Kanwil grid + KPP drawer */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Kanwil cards */}
              <div className="xl:col-span-2">
                <h2 className="text-lg font-semibold text-gray-200 mb-4">
                  Statistik per Kanwil DJP
                  <span className="ml-2 text-sm text-gray-500">({kanwilList.length} Kanwil)</span>
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[70vh] overflow-y-auto pr-1">
                  {kanwilList
                    .sort((a, b) => b.taxpayer_count - a.taxpayer_count)
                    .map((kw) => {
                      const isSelected = selectedKanwil?.kanwil_id === kw.kanwil_id;
                      return (
                        <button
                          key={kw.kanwil_id}
                          onClick={() => handleKanwilClick(kw)}
                          className={`text-left bg-gray-900 border rounded-xl p-4 transition-all ${
                            isSelected
                              ? 'border-blue-500 ring-1 ring-blue-500'
                              : 'border-gray-700 hover:border-gray-500'
                          }`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <div className="text-sm font-semibold text-white leading-tight">
                                {kw.kanwil_name}
                              </div>
                              <div className="text-xs text-gray-500">{kw.kanwil_code}</div>
                            </div>
                            <span className="text-xs text-gray-500 bg-gray-800 rounded px-2 py-0.5">
                              {kw.kpp_count} KPP
                            </span>
                          </div>

                          <div className="flex justify-between items-end mt-2">
                            <div>
                              <div className="text-lg font-bold text-blue-400">
                                {kw.taxpayer_count.toLocaleString('id-ID')}
                              </div>
                              <div className="text-xs text-gray-500">WP</div>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-semibold text-purple-400">
                                {kw.group_count.toLocaleString('id-ID')}
                              </div>
                              <div className="text-xs text-gray-500">Grup</div>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-semibold text-red-400">
                                {kw.detection_count.toLocaleString('id-ID')}
                              </div>
                              <div className="text-xs text-gray-500">Deteksi</div>
                            </div>
                          </div>
                          <MiniBar value={kw.taxpayer_count} max={maxTp} />

                          {/* Risk indicators */}
                          <div className="flex gap-2 mt-2 flex-wrap">
                            {kw.shell_candidate_count > 0 && (
                              <span className="text-xs bg-orange-900/50 text-orange-300 rounded px-1.5 py-0.5">
                                🐚 {kw.shell_candidate_count} shell
                              </span>
                            )}
                            {kw.vat_carousel_count > 0 && (
                              <span className="text-xs bg-yellow-900/50 text-yellow-300 rounded px-1.5 py-0.5">
                                🎠 {kw.vat_carousel_count} carousel
                              </span>
                            )}
                          </div>

                          {isSelected && (
                            <div className="mt-2 text-xs text-blue-400">
                              ▼ Lihat KPP →
                            </div>
                          )}
                        </button>
                      );
                    })}
                </div>
              </div>

              {/* KPP drill-down */}
              <div className="xl:col-span-1">
                {selectedKanwil ? (
                  <div className="bg-gray-900 border border-gray-700 rounded-2xl p-4">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-bold text-white">{selectedKanwil.kanwil_name}</h3>
                        <p className="text-xs text-gray-400 mt-1">Daftar KPP</p>
                      </div>
                      <button
                        onClick={() => { setSelectedKanwil(null); setKppList([]); }}
                        className="text-gray-500 hover:text-gray-300 text-xs"
                      >
                        ✕
                      </button>
                    </div>

                    {kppLoading && (
                      <div className="text-center text-gray-400 py-8">
                        <div className="text-2xl animate-spin mb-2">⚙️</div>
                        <div className="text-xs">Memuat KPP…</div>
                      </div>
                    )}

                    {!kppLoading && kppList.length === 0 && (
                      <div className="text-gray-500 text-sm text-center py-8">
                        Tidak ada KPP ditemukan
                      </div>
                    )}

                    {!kppLoading && kppList.length > 0 && (
                      <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                        {kppList.map((kpp) => (
                          <div
                            key={kpp.kpp_id}
                            className="bg-gray-800 rounded-lg p-3 border border-gray-700"
                          >
                            <div className="flex items-start justify-between mb-1">
                              <div className="text-xs font-semibold text-white">{kpp.kpp_name}</div>
                              <span className="text-xs text-gray-500 font-mono">{kpp.kpp_code}</span>
                            </div>
                            {kpp.city_name && (
                              <div className="text-xs text-gray-500 mb-2">📍 {kpp.city_name}</div>
                            )}
                            <div className="grid grid-cols-3 gap-1 text-center">
                              <div>
                                <div className="text-sm font-bold text-blue-400">
                                  {kpp.taxpayer_count.toLocaleString('id-ID')}
                                </div>
                                <div className="text-xs text-gray-500">WP</div>
                              </div>
                              <div>
                                <div className="text-sm font-bold text-purple-400">
                                  {kpp.group_count.toLocaleString('id-ID')}
                                </div>
                                <div className="text-xs text-gray-500">Grup</div>
                              </div>
                              <div>
                                <div className="text-sm font-bold text-red-400">
                                  {kpp.detection_count.toLocaleString('id-ID')}
                                </div>
                                <div className="text-xs text-gray-500">Deteksi</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 text-center">
                    <div className="text-4xl mb-3">🏬</div>
                    <div className="text-sm font-semibold text-gray-300 mb-1">Drill-down KPP</div>
                    <div className="text-xs text-gray-500">
                      Klik kartu Kanwil di sebelah kiri untuk melihat statistik KPP-nya
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}
