'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Sidebar from './Sidebar';
import { authApi } from '@/lib/api';

interface MainLayoutProps {
  children: React.ReactNode;
  title?: string;
  showHeader?: boolean;
}

export default function MainLayout({ children, title, showHeader = true }: MainLayoutProps) {
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  const { data: user, isLoading: userLoading } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await authApi.me();
      return response.data;
    },
    retry: false,
  });

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
    }
  }, [user, userLoading, router]);

  // Check screen size on mount
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setSidebarCollapsed(false);
      } else {
        setSidebarCollapsed(true);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleLogout = async () => {
    await authApi.logout();
    router.push('/login');
  };

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
      <Sidebar
        user={user}
        onLogout={handleLogout}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Content Area */}
      <div
        className={`
          transition-all duration-300
          ${sidebarCollapsed ? 'lg:ml-20' : 'lg:ml-72'}
        `}
      >
        {showHeader && (
          <header className="border-b-2 border-white/80 bg-white/80 backdrop-blur-xl shadow-sm sticky top-0 z-30">
            <div className="px-4 sm:px-6 lg:px-8 py-4">
              <div className="flex items-center justify-between">
                {/* Mobile menu toggle */}
                <button
                  onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                  className="p-2 rounded-lg hover:bg-indigo-50 text-gray-600 hover:text-indigo-600 transition-colors lg:hidden"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>

                {/* Page Title */}
                {title && (
                  <h1 className="text-xl font-bold text-gray-900">{title}</h1>
                )}

                {/* Desktop header content */}
                <div className="flex items-center gap-4 ml-auto">
                  <div className="hidden sm:flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-100 px-4 py-2 shadow-sm">
                    <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-sm font-semibold text-gray-800">{user.username}</span>
                    <span className="text-xs text-indigo-600 font-bold">{user.role}</span>
                  </div>
                </div>
              </div>
            </div>
          </header>
        )}

        <main className="p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}