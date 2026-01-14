'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import SearchBar from '@/components/SearchBar';
import { authApi, groupsApi } from '@/lib/api';

export default function HomePage() {
  const router = useRouter();

  const { data: user, isLoading: userLoading } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await authApi.me();
      return response.data;
    },
    retry: false,
  });

  const { data: groups = [] } = useQuery({
    queryKey: ['groups-preview'],
    queryFn: async () => {
      const response = await groupsApi.list(1, 6);
      return response.data;
    },
    enabled: !!user,
  });

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
    }
  }, [user, userLoading, router]);

  if (userLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="relative">
          <div className="animate-spin h-16 w-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full" />
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <div className="h-8 w-8 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-full animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen">
      {/* Enhanced Header */}
      <header className="border-b-2 border-white/80 bg-white/80 backdrop-blur-xl shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 shadow-lg flex items-center justify-center">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">smartweb</h1>
                <p className="text-xs text-gray-600 font-medium">Task Force Wajib Pajak Grup 2026</p>
              </div>
            </div>
            <nav className="hidden md:flex items-center gap-8 text-sm font-semibold">
              <button onClick={() => router.push('/')} className="text-indigo-600 hover:text-indigo-700 transition-colors">Home</button>
              <button onClick={() => router.push('/search')} className="text-gray-600 hover:text-gray-900 transition-colors">Search</button>
              <button onClick={() => router.push('/network')} className="text-gray-600 hover:text-gray-900 transition-colors">Network</button>
              {user.role === 'Admin' && (
                <button onClick={() => router.push('/admin')} className="text-gray-600 hover:text-gray-900 transition-colors">Admin</button>
              )}
            </nav>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-100 px-4 py-2 shadow-sm">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
                <span className="text-sm font-semibold text-gray-800">{user.username}</span>
                <span className="text-xs text-indigo-600 font-bold">{user.role}</span>
              </div>
              <button
                onClick={async () => {
                  await authApi.logout();
                  router.push('/login');
                }}
                className="btn-secondary text-sm px-4 py-2"
              >
                Keluar
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-16">
        {/* Hero Section */}
        <section className="grid grid-cols-1 lg:grid-cols-[1.05fr_0.95fr] gap-12 items-center">
          <div className="space-y-6">
            <span className="inline-flex items-center gap-2 px-4 py-2 text-xs uppercase tracking-widest text-indigo-600 bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-100 rounded-full font-bold shadow-sm">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              Smart Intelligence
            </span>
            <h2 className="text-5xl md:text-6xl font-bold text-gray-900 leading-tight">
              Elevate Your Digital
              <br />
              <span className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                Experience
              </span>
            </h2>
            <p className="text-lg text-gray-600 max-w-xl leading-relaxed">
              Akses cepat untuk memetakan grup wajib pajak, beneficial owner, dan relasi strategis
              melalui pencarian presisi dan network graph yang terkendali.
            </p>
            <div className="flex flex-wrap gap-4">
              <button onClick={() => router.push('/search')} className="btn-primary flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Mulai Pencarian
              </button>
              <button onClick={() => router.push('/network')} className="btn-secondary flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
                Lihat Network
              </button>
            </div>
            <div className="mt-8">
              <SearchBar />
            </div>
          </div>

          {/* Stats Panel */}
          <div className="relative">
            <div className="absolute -top-8 -left-6 h-32 w-32 rounded-full bg-indigo-300/40 blur-3xl animate-pulse" />
            <div className="absolute bottom-4 -right-8 h-36 w-36 rounded-full bg-purple-300/40 blur-3xl animate-pulse" style={{animationDelay: '1s'}} />
            <div className="glass-panel p-8 space-y-6 relative">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest text-indigo-600 font-bold">Ringkasan</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">Data Intelligence</p>
                </div>
                <span className="text-xs text-gray-500 bg-gray-100 px-3 py-1 rounded-full font-semibold">2022-2025</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-2xl bg-gradient-to-br from-indigo-50 to-indigo-100/50 border-2 border-indigo-100 p-5 hover:shadow-lg transition-all">
                  <p className="text-xs text-indigo-600 font-bold uppercase tracking-wide">Grup Terdaftar</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">100+</p>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-purple-50 to-purple-100/50 border-2 border-purple-100 p-5 hover:shadow-lg transition-all">
                  <p className="text-xs text-purple-600 font-bold uppercase tracking-wide">Wajib Pajak</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">1500+</p>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-pink-50 to-pink-100/50 border-2 border-pink-100 p-5 hover:shadow-lg transition-all">
                  <p className="text-xs text-pink-600 font-bold uppercase tracking-wide">Beneficial Owner</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">300+</p>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100/50 border-2 border-blue-100 p-5 hover:shadow-lg transition-all">
                  <p className="text-xs text-blue-600 font-bold uppercase tracking-wide">Depth Network</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">Up to 5</p>
                </div>
              </div>
              <div className="text-xs text-gray-600 bg-gray-50 rounded-xl p-3 border border-gray-100">
                <svg className="w-4 h-4 inline mr-1 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                Gunakan depth tinggi dengan batas node yang aman sesuai peran.
              </div>
            </div>
          </div>
        </section>

        {/* Quick Access Section */}
        <section>
          <h3 className="section-title mb-6 flex items-center gap-3">
            <span className="h-1 w-12 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-full"></span>
            Akses Cepat
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <button
              onClick={() => router.push('/search?entity_type=GROUP')}
              className="card group hover:scale-105 cursor-pointer text-left"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
              </div>
              <h4 className="font-bold text-xl text-indigo-700 mb-2">Daftar Grup</h4>
              <p className="text-sm text-gray-600">Lihat semua grup wajib pajak</p>
            </button>

            <button
              onClick={() => router.push('/search?entity_type=TAXPAYER')}
              className="card group hover:scale-105 cursor-pointer text-left"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
              </div>
              <h4 className="font-bold text-xl text-emerald-700 mb-2">Daftar Wajib Pajak</h4>
              <p className="text-sm text-gray-600">Lihat semua wajib pajak</p>
            </button>

            <button
              onClick={() => router.push('/search?entity_type=BENEFICIAL_OWNER')}
              className="card group hover:scale-105 cursor-pointer text-left"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
              </div>
              <h4 className="font-bold text-xl text-purple-700 mb-2">Beneficial Owners</h4>
              <p className="text-sm text-gray-600">Lihat semua beneficial owner</p>
            </button>

            <button
              onClick={() => router.push('/network')}
              className="card group hover:scale-105 cursor-pointer text-left"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-pink-500 to-pink-600 flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                </div>
              </div>
              <h4 className="font-bold text-xl text-pink-700 mb-2">Network Graph</h4>
              <p className="text-sm text-gray-600">Visualisasi jaringan WP dan BO</p>
            </button>
          </div>
        </section>

        {/* Recent Groups */}
        {groups.length > 0 && (
          <section>
            <h3 className="section-title mb-6 flex items-center gap-3">
              <span className="h-1 w-12 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full"></span>
              Grup Terbaru
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {groups.map((group: any) => (
                <div
                  key={group.id}
                  onClick={() => router.push(`/groups/${group.id}`)}
                  className="card cursor-pointer group hover:scale-105"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
                      <svg className="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
                      </svg>
                    </div>
                  </div>
                  <h4 className="font-bold text-lg text-gray-900 mb-1 group-hover:text-indigo-600 transition-colors">{group.name}</h4>
                  <p className="text-sm text-gray-600 mb-3">{group.sector || 'Tidak ada sektor'}</p>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full font-semibold">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                      </svg>
                      {group.member_count || 0} anggota
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
