'use client';

import { useEffect, useState } from 'react';
import MainLayout from '@/components/MainLayout';
import GoogleMapEmbed from '@/components/GoogleMapEmbed';
import { groupMapApi } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type CityMarker = {
  kanwil_id: number;
  kanwil_name: string;
  kanwil_code: string;
  lat: number;
  lon: number;
  taxpayer_count: number;
  group_count: number;
  bo_count: number;
  high_risk_count: number;
  foreign_entity_count: number;
  relationship_count: number;
};

// ---------------------------------------------------------------------------
// Indonesia bounding box → SVG coordinate mapping
// ---------------------------------------------------------------------------
const MAP_W = 900;
const MAP_H = 400;
const LON_MIN = 95.0;
const LON_MAX = 141.0;
const LAT_MIN = -11.0;
const LAT_MAX = 6.0;

function toSvg(lat: number, lon: number): [number, number] {
  const x = ((lon - LON_MIN) / (LON_MAX - LON_MIN)) * MAP_W;
  const y = ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * MAP_H;
  return [x, y];
}

// ---------------------------------------------------------------------------
// Simple Indonesia outline as SVG path (simplified polygon)
// ---------------------------------------------------------------------------
const INDONESIA_ISLANDS = [
  // Sumatra (simplified)
  'M 110,40 L 120,35 L 140,50 L 150,80 L 145,110 L 135,120 L 120,115 L 108,100 L 105,70 Z',
  // Java (simplified)
  'M 150,130 L 165,125 L 200,128 L 230,132 L 240,138 L 235,145 L 200,148 L 165,145 L 148,140 Z',
  // Kalimantan (simplified)
  'M 155,60 L 175,45 L 210,42 L 235,50 L 245,75 L 240,105 L 225,120 L 195,125 L 168,115 L 155,90 Z',
  // Sulawesi (simplified)
  'M 245,65 L 258,55 L 270,65 L 265,85 L 270,100 L 260,115 L 250,108 L 242,90 L 248,75 Z',
  // Papua (simplified)
  'M 330,70 L 360,60 L 390,65 L 410,80 L 415,105 L 405,130 L 385,140 L 360,138 L 335,125 L 325,100 Z',
  // Bali + Lombok
  'M 242,148 L 250,144 L 260,147 L 262,155 L 252,158 L 242,155 Z',
  // Maluku (simplified)
  'M 290,85 L 300,78 L 310,82 L 312,92 L 305,98 L 295,94 Z',
];

// ---------------------------------------------------------------------------
// Colour scale by count
// ---------------------------------------------------------------------------
function markerColor(count: number, max: number): string {
  const ratio = count / max;
  if (ratio > 0.7) return '#ef4444';
  if (ratio > 0.4) return '#f97316';
  if (ratio > 0.2) return '#eab308';
  return '#22c55e';
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function PetaSebaranPage() {
  const [markers, setMarkers] = useState<CityMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<CityMarker | null>(null);
  const [year, setYear] = useState<number>(new Date().getFullYear() - 1);
  const [metric, setMetric] = useState<keyof CityMarker>('taxpayer_count');

  useEffect(() => {
    setLoading(true);
    setError(null);
    groupMapApi
      .summary(year)
      .then((res) => {
        const data: CityMarker[] = res.data.markers || [];
        setMarkers(data);
      })
      .catch(() => setError('Gagal memuat data peta. Pastikan server berjalan.'))
      .finally(() => setLoading(false));
  }, [year]);

  const maxVal = Math.max(...markers.map((m) => Number(m[metric]) || 0), 1);

  const yearOptions = Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i);

  const METRIC_LABELS: Record<string, string> = {
    taxpayer_count: 'Wajib Pajak',
    group_count: 'Grup',
    bo_count: 'Beneficial Owner',
    high_risk_count: 'Entitas Risiko Tinggi',
    relationship_count: 'Total Relasi',
  };

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-950 text-white p-6">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              🗺️ Peta Sebaran Group WP
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Distribusi geografis entitas wajib pajak per Kanwil DJP
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Year selector */}
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-600 focus:outline-none focus:border-blue-500"
            >
              {yearOptions.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            {/* Metric selector */}
            <select
              value={metric as string}
              onChange={(e) => setMetric(e.target.value as keyof CityMarker)}
              className="bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-600 focus:outline-none focus:border-blue-500"
            >
              {Object.entries(METRIC_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center h-80">
            <div className="text-center text-gray-400">
              <div className="text-4xl animate-spin mb-4">⚙️</div>
              <div>Memuat data peta…</div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-4 mb-6">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
            {/* MAP */}
            <div className="xl:col-span-3 bg-gray-900 rounded-2xl border border-gray-700 overflow-hidden">
              <div className="p-4 border-b border-gray-700 flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-300">
                  Peta Indonesia — {METRIC_LABELS[metric as string]}
                </span>
                <div className="flex items-center gap-4 text-xs text-gray-400">
                  {[
                    { color: '#22c55e', label: 'Rendah' },
                    { color: '#eab308', label: 'Sedang' },
                    { color: '#f97316', label: 'Tinggi' },
                    { color: '#ef4444', label: 'Sangat Tinggi' },
                  ].map(({ color, label }) => (
                    <div key={label} className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded-full" style={{ background: color }} />
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="relative p-4">
                <svg
                  viewBox={`0 0 ${MAP_W} ${MAP_H}`}
                  className="w-full"
                  style={{ background: '#0f172a' }}
                >
                  {/* Ocean background */}
                  <rect width={MAP_W} height={MAP_H} fill="#0f172a" />

                  {/* Indonesia island outlines (simplified) */}
                  {INDONESIA_ISLANDS.map((d, i) => (
                    <path
                      key={i}
                      d={d}
                      fill="#1e3a5f"
                      stroke="#2563eb"
                      strokeWidth="0.5"
                      opacity="0.7"
                    />
                  ))}

                  {/* Kanwil markers */}
                  {markers.map((m) => {
                    const val = Number(m[metric]) || 0;
                    const [cx, cy] = toSvg(m.lat, m.lon);
                    const r = Math.max(6, Math.min(28, 6 + (val / maxVal) * 22));
                    const color = markerColor(val, maxVal);
                    const isSelected = selected?.kanwil_id === m.kanwil_id;

                    return (
                      <g
                        key={m.kanwil_id}
                        onClick={() => setSelected(isSelected ? null : m)}
                        style={{ cursor: 'pointer' }}
                      >
                        <circle
                          cx={cx}
                          cy={cy}
                          r={r + 4}
                          fill={color}
                          opacity={0.15}
                        />
                        <circle
                          cx={cx}
                          cy={cy}
                          r={r}
                          fill={color}
                          opacity={0.85}
                          stroke={isSelected ? '#fff' : color}
                          strokeWidth={isSelected ? 2 : 0.5}
                        />
                        <text
                          x={cx}
                          y={cy + 1}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fontSize={r > 10 ? 8 : 6}
                          fill="white"
                          fontWeight="bold"
                        >
                          {m.kanwil_code || ''}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>

            {/* SIDE PANEL */}
            <div className="xl:col-span-1 flex flex-col gap-4">
              {/* Selected detail */}
              {selected ? (
                <div className="bg-gray-900 rounded-2xl border border-blue-700 p-4">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-sm font-bold text-white">{selected.kanwil_name}</h3>
                    <button
                      onClick={() => setSelected(null)}
                      className="text-gray-500 hover:text-gray-300 text-xs"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="text-xs text-gray-400 mb-3">{selected.kanwil_code}</div>
                  <div className="space-y-2 mb-4">
                    {[
                      { label: 'Wajib Pajak', value: selected.taxpayer_count, color: 'text-blue-400' },
                      { label: 'Grup', value: selected.group_count, color: 'text-purple-400' },
                      { label: 'Beneficial Owner', value: selected.bo_count, color: 'text-emerald-400' },
                      { label: 'Risiko Tinggi', value: selected.high_risk_count, color: 'text-red-400' },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="flex justify-between items-center">
                        <span className="text-xs text-gray-400">{label}</span>
                        <span className={`text-sm font-bold ${color}`}>
                          {value?.toLocaleString('id-ID') || 0}
                        </span>
                      </div>
                    ))}
                  </div>
                  <GoogleMapEmbed
                    q={`${selected.kanwil_name}, Indonesia`}
                    zoom={10}
                    height={200}
                  />
                </div>
              ) : (
                <div className="bg-gray-900 rounded-2xl border border-gray-700 p-4 text-center text-gray-500 text-sm">
                  Klik marker pada peta untuk melihat detail Kanwil
                </div>
              )}

              {/* Top 5 Kanwil */}
              <div className="bg-gray-900 rounded-2xl border border-gray-700 p-4">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">
                  Top Kanwil — {METRIC_LABELS[metric as string]}
                </h3>
                <div className="space-y-2">
                  {[...markers]
                    .sort((a, b) => (Number(b[metric]) || 0) - (Number(a[metric]) || 0))
                    .slice(0, 8)
                    .map((m, i) => {
                      const val = Number(m[metric]) || 0;
                      return (
                        <button
                          key={m.kanwil_id}
                          onClick={() => setSelected(m)}
                          className="w-full flex items-center gap-2 text-left hover:bg-gray-800 rounded p-1 transition-colors"
                        >
                          <span className="text-xs text-gray-500 w-4">{i + 1}</span>
                          <div className="flex-1 min-w-0">
                            <div className="text-xs text-white truncate">{m.kanwil_name}</div>
                            <div className="text-xs text-gray-500">{m.kanwil_code}</div>
                          </div>
                          <span className="text-xs font-bold text-blue-400 shrink-0">
                            {val.toLocaleString('id-ID')}
                          </span>
                        </button>
                      );
                    })}
                </div>
              </div>

              {/* Summary totals */}
              <div className="bg-gray-900 rounded-2xl border border-gray-700 p-4">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">Nasional</h3>
                <div className="space-y-1 text-xs">
                  {[
                    { label: 'Kanwil', value: markers.length },
                    { label: 'Total WP', value: markers.reduce((s, m) => s + (m.taxpayer_count || 0), 0) },
                    { label: 'Total Grup', value: markers.reduce((s, m) => s + (m.group_count || 0), 0) },
                    { label: 'Total BO', value: markers.reduce((s, m) => s + (m.bo_count || 0), 0) },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex justify-between">
                      <span className="text-gray-400">{label}</span>
                      <span className="text-white font-medium">{value.toLocaleString('id-ID')}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
