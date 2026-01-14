'use client';

import { useRouter } from 'next/navigation';
import SearchBar from '@/components/SearchBar';

export default function SearchPage() {
  const router = useRouter();
  return (
    <div className="min-h-screen">
      <header className="bg-white/70 backdrop-blur border-b border-white/60">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-400 shadow-md" />
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Pencarian</h1>
              <p className="text-xs text-gray-500">SmartWeb Search Hub</p>
            </div>
          </div>
          <button onClick={() => router.push('/')} className="btn-secondary text-sm">Beranda</button>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-10">
        <div className="glass-panel p-6">
          <SearchBar />
          <p className="mt-4 text-sm text-gray-600">Masukkan kata kunci pencarian di atas</p>
        </div>
      </main>
    </div>
  );
}
