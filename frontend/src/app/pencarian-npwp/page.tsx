'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/MainLayout';

export default function PencarianNPWPPage() {
  const router = useRouter();
  const [tahunPajak, setTahunPajak] = useState('2024');
  const [npwp, setNpwp] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!npwp.trim()) return;

    setIsSearching(true);
    // Navigate to the network page with the NPWP as parameter
    router.push(`/jaringan-wp?npwp=${encodeURIComponent(npwp)}&year=${tahunPajak}`);
  };

  const years = ['2025', '2024', '2023', '2022', '2021', '2020'];

  return (
    <MainLayout title="Pencarian NPWP">
      <div className="max-w-2xl mx-auto">
        <div className="glass-panel p-8">
          <div className="flex items-center gap-4 mb-6">
            <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16l2.879-2.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Pencarian NPWP</h2>
              <p className="text-gray-600">Cari wajib pajak berdasarkan NPWP</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="tahunPajak" className="block text-sm font-bold text-gray-700 mb-2">
                Tahun Pajak
              </label>
              <select
                id="tahunPajak"
                value={tahunPajak}
                onChange={(e) => setTahunPajak(e.target.value)}
                className="input-field"
              >
                {years.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="npwp" className="block text-sm font-bold text-gray-700 mb-2">
                NPWP
              </label>
              <input
                type="text"
                id="npwp"
                value={npwp}
                onChange={(e) => setNpwp(e.target.value)}
                placeholder="Masukkan NPWP (contoh: 01.234.567.8-901.000)"
                className="input-field"
              />
              <p className="mt-2 text-xs text-gray-500">
                Format: XX.XXX.XXX.X-XXX.XXX atau tanpa tanda baca
              </p>
            </div>

            <button
              type="submit"
              disabled={!npwp.trim() || isSearching}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSearching ? (
                <>
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Mencari...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <span>Cari</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Quick Tips */}
        <div className="mt-6 p-4 bg-indigo-50 rounded-xl border border-indigo-100">
          <h3 className="text-sm font-bold text-indigo-700 mb-2">Tips Pencarian</h3>
          <ul className="text-sm text-indigo-600 space-y-1">
            <li>• NPWP dapat dimasukkan dengan atau tanpa tanda baca</li>
            <li>• Hasil pencarian akan menampilkan jaringan wajib pajak</li>
            <li>• Double-click pada node untuk memperluas jaringan</li>
          </ul>
        </div>
      </div>
    </MainLayout>
  );
}