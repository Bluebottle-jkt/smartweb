'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '@/lib/api';

export default function AdminPage() {
  const router = useRouter();
  const [isResetting, setIsResetting] = useState(false);
  const [isDeriving, setIsDeriving] = useState(false);

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: async () => {
      const response = await adminApi.stats();
      return response.data;
    },
  });

  const handleReset = async () => {
    if (!confirm('PERINGATAN: Ini akan menghapus semua data dan membuat ulang seed data. Lanjutkan?')) return;

    setIsResetting(true);
    try {
      await adminApi.resetAndSeed();
      alert('Database berhasil di-reset dan di-seed ulang!');
      window.location.reload();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Gagal mereset database');
    } finally {
      setIsResetting(false);
    }
  };

  const handleDeriveGroups = async () => {
    if (!confirm('Generate derived groups dari relationship graph?')) return;

    setIsDeriving(true);
    try {
      const response = await adminApi.deriveGroups();
      const summary = response.data.summary;
      alert(`Berhasil! ${summary.number_of_groups} grup derivasi dibuat dengan ${summary.total_memberships} memberships. Runtime: ${summary.runtime_ms}ms`);
      refetchStats();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Gagal men-derive groups');
    } finally {
      setIsDeriving(false);
    }
  };

  return (
    <div className="min-h-screen">
      <header className="bg-white/70 backdrop-blur border-b border-white/60">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <button onClick={() => router.push('/')} className="btn-secondary mb-2">← Beranda</button>
          <h1 className="text-2xl font-bold">Panel Admin</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        <div className="card">
          <h3 className="font-semibold text-lg mb-4">Statistik Sistem</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="p-4 bg-blue-50 rounded">
              <p className="text-sm text-gray-600">Total Grup</p>
              <p className="text-2xl font-bold">{stats?.groups || 0}</p>
            </div>
            <div className="p-4 bg-green-50 rounded">
              <p className="text-sm text-gray-600">Total Wajib Pajak</p>
              <p className="text-2xl font-bold">{stats?.taxpayers || 0}</p>
            </div>
            <div className="p-4 bg-purple-50 rounded">
              <p className="text-sm text-gray-600">Total Beneficial Owners</p>
              <p className="text-2xl font-bold">{stats?.beneficial_owners || 0}</p>
            </div>
            <div className="p-4 bg-yellow-50 rounded">
              <p className="text-sm text-gray-600">Relationships</p>
              <p className="text-2xl font-bold">{stats?.relationships || 0}</p>
            </div>
            <div className="p-4 bg-indigo-50 rounded">
              <p className="text-sm text-gray-600">Derived Groups</p>
              <p className="text-2xl font-bold">{stats?.derived_groups || 0}</p>
            </div>
          </div>
        </div>

        <div className="card bg-blue-50 border-blue-200">
          <h3 className="font-semibold text-lg mb-4 text-blue-900">Derived Groups</h3>
          <p className="text-sm text-blue-700 mb-4">
            Generate grup derivasi dari relationship graph menggunakan rule set aktif.
          </p>
          <button
            onClick={handleDeriveGroups}
            disabled={isDeriving}
            className="btn-primary bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {isDeriving ? 'Memproses...' : 'Generate Derived Groups'}
          </button>
        </div>

        <div className="card bg-red-50 border-red-200">
          <h3 className="font-semibold text-lg mb-4 text-red-900">Zona Berbahaya</h3>
          <p className="text-sm text-red-700 mb-4">
            Aksi berikut akan menghapus SEMUA data dan membuat ulang seed data. Gunakan hanya untuk development!
          </p>
          <button
            onClick={handleReset}
            disabled={isResetting}
            className="btn-primary bg-red-600 hover:bg-red-700 disabled:opacity-50"
          >
            {isResetting ? 'Memproses...' : 'Reset Database & Re-seed'}
          </button>
        </div>
      </main>
    </div>
  );
}
