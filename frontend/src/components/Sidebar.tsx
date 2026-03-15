'use client';

import { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

interface MenuItem {
  label: string;
  path?: string;
  icon?: React.ReactNode;
  children?: MenuItem[];
  defaultExpanded?: boolean;
  badge?: string;
}

interface SidebarProps {
  user: { username: string; role: string } | null;
  onLogout: () => void;
  collapsed?: boolean;
  onToggle?: () => void;
}

// ---------------------------------------------------------------------------
// SVG Icons
// ---------------------------------------------------------------------------
const Icon = ({ d }: { d: string }) => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={d} />
  </svg>
);

const ICONS = {
  dashboard:   "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
  map:         "M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7",
  stats:       "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  network:     "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1",
  intelligence:"M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z",
  ownership:   "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  bo:          "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
  group:       "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z",
  search:      "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  transaction: "M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4",
  shield:      "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  cycle:       "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
  pyramid:     "M3 21h18M3 10h18M3 6l9-3 9 3M4 10h16v11H4z",
  shell:       "M20.618 5.984A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  nominee:     "M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2",
  assistant:   "M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z",
  admin:       "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
  chevron:     "M19 9l-7 7-7-7",
  logout:      "M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1",
  menu:        "M4 6h16M4 12h16M4 18h16",
  close:       "M6 18L18 6M6 6l12 12",
  subsidiary:  "M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9",
  family:      "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z",
  director:    "M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  controller:  "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  company:     "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
};

// ---------------------------------------------------------------------------
// Menu structure (consolidated – no duplicate Kepemilikan top-level)
// ---------------------------------------------------------------------------
const menuItems: MenuItem[] = [
  {
    label: 'Dashboard',
    path: '/',
    icon: <Icon d={ICONS.dashboard} />,
  },
  {
    label: 'Peta Sebaran Group',
    path: '/peta-sebaran',
    icon: <Icon d={ICONS.map} />,
  },
  {
    label: 'Statistik DJP',
    path: '/statistik-djp',
    icon: <Icon d={ICONS.stats} />,
    badge: 'Baru',
  },
  {
    label: 'Graph Intelligence',
    icon: <Icon d={ICONS.intelligence} />,
    defaultExpanded: true,
    children: [
      { label: 'Graph Explorer',           path: '/network-explorer',              icon: <Icon d={ICONS.network} />, badge: 'v2' },
      { label: 'Jaringan Wajib Pajak',     path: '/jaringan-wp',                   icon: <Icon d={ICONS.network} /> },
      { label: 'Struktur Kepemilikan',     path: '/kepemilikan/struktur',          icon: <Icon d={ICONS.ownership} /> },
      { label: 'Beneficial Owner',         path: '/kepemilikan/beneficial-owner',  icon: <Icon d={ICONS.bo} /> },
      { label: 'Group WP',                 path: '/kepemilikan/group',             icon: <Icon d={ICONS.group} /> },
      { label: 'Pengendali',               path: '/kepemilikan/pengendali',        icon: <Icon d={ICONS.controller} /> },
      { label: 'Anak Usaha',               path: '/kepemilikan/anak-usaha',        icon: <Icon d={ICONS.subsidiary} /> },
      { label: 'Keluarga Pemegang Saham',  path: '/kepemilikan/keluarga',          icon: <Icon d={ICONS.family} /> },
      { label: 'Group Pengurus',           path: '/kepemilikan/pengurus',          icon: <Icon d={ICONS.director} /> },
      { label: 'Deteksi Siklus',           path: '/network-explorer?detector=circular',   icon: <Icon d={ICONS.cycle} /> },
      { label: 'Piramida Kepemilikan',     path: '/network-explorer?detector=pyramid',    icon: <Icon d={ICONS.pyramid} /> },
      { label: 'Shell Company',            path: '/network-explorer?detector=shell',      icon: <Icon d={ICONS.shell} /> },
      { label: 'Nominee Direksi',          path: '/network-explorer?detector=nominee',    icon: <Icon d={ICONS.nominee} /> },
    ],
  },
  {
    label: 'Pencarian & Eksplorasi',
    icon: <Icon d={ICONS.search} />,
    children: [
      { label: 'Pencarian NPWP',    path: '/pencarian-npwp',    icon: <Icon d={ICONS.search} /> },
      { label: 'Explorasi Manual',  path: '/explorasi-manual',  icon: <Icon d={ICONS.network} /> },
      { label: 'Transaksi Bisnis',  path: '/transaksi-bisnis',  icon: <Icon d={ICONS.transaction} /> },
      { label: 'Perusahaan',        path: '/kepemilikan/perusahaan', icon: <Icon d={ICONS.company} /> },
    ],
  },
  {
    label: 'Manajemen Grup',
    icon: <Icon d={ICONS.group} />,
    children: [
      { label: 'Daftar Grup',   path: '/group-menu',   icon: <Icon d={ICONS.group} /> },
    ],
  },
  {
    label: 'Asisten AI',
    path: '/assistant',
    icon: <Icon d={ICONS.assistant} />,
    badge: 'Baru',
  },
  {
    label: 'Admin',
    path: '/admin',
    icon: <Icon d={ICONS.admin} />,
  },
];

// ---------------------------------------------------------------------------
// Chevron Icon
// ---------------------------------------------------------------------------
const ChevronIcon = ({ open }: { open: boolean }) => (
  <svg
    className={`w-4 h-4 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
    fill="none" stroke="currentColor" viewBox="0 0 24 24"
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICONS.chevron} />
  </svg>
);

// ---------------------------------------------------------------------------
// Sidebar component
// ---------------------------------------------------------------------------
export default function Sidebar({ user, onLogout, collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [expandedSections, setExpandedSections] = useState<string[]>(['Graph Intelligence']);

  const toggleSection = (label: string) =>
    setExpandedSections((prev) =>
      prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label]
    );

  const isActive = (path?: string) => {
    if (!path) return false;
    // Strip query params for active check
    const pathNoQuery = path.split('?')[0];
    return pathname === pathNoQuery || pathname.startsWith(pathNoQuery + '/');
  };

  const renderMenuItem = (item: MenuItem, depth = 0) => {
    const hasChildren = !!item.children?.length;
    const isExpanded = expandedSections.includes(item.label);
    const active = isActive(item.path);

    return (
      <div key={item.label}>
        <button
          onClick={() => {
            if (hasChildren) toggleSection(item.label);
            else if (item.path) router.push(item.path);
          }}
          className={`
            w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-xl transition-all duration-200
            ${depth > 0 ? 'ml-4 px-3 py-2 text-xs' : ''}
            ${active
              ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg'
              : 'text-gray-700 hover:bg-indigo-50 hover:text-indigo-700'}
          `}
        >
          <span className={active ? 'text-white' : 'text-indigo-500'}>
            {item.icon}
          </span>
          {!collapsed && (
            <>
              <span className="flex-1 text-left truncate">{item.label}</span>
              {item.badge && (
                <span className="px-1.5 py-0.5 text-xs rounded-full bg-emerald-500 text-white font-bold shrink-0">
                  {item.badge}
                </span>
              )}
              {hasChildren && <ChevronIcon open={isExpanded} />}
            </>
          )}
        </button>

        {hasChildren && isExpanded && !collapsed && (
          <div className="mt-1 space-y-0.5">
            {item.children!.map((child) => renderMenuItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Mobile overlay */}
      {!collapsed && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 h-full bg-white/95 backdrop-blur-xl border-r-2 border-indigo-100
          shadow-2xl z-50 transition-all duration-300 flex flex-col
          ${collapsed ? 'w-20' : 'w-72'}
          lg:translate-x-0
          ${collapsed ? '-translate-x-full lg:translate-x-0' : 'translate-x-0'}
        `}
      >
        {/* Header */}
        <div className="p-4 border-b-2 border-indigo-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 shadow-lg flex items-center justify-center shrink-0">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              {!collapsed && (
                <div>
                  <h1 className="text-sm font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                    SmartWeb
                  </h1>
                  <p className="text-xs text-gray-500">Graph Intelligence v2.0</p>
                </div>
              )}
            </div>
            <button
              onClick={onToggle}
              className="p-2 rounded-lg hover:bg-indigo-50 text-gray-600 hover:text-indigo-600 transition-colors lg:hidden"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICONS.close} />
              </svg>
            </button>
          </div>
        </div>

        {/* Menu */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {menuItems.map((item) => renderMenuItem(item))}
        </nav>

        {/* User footer */}
        <div className="p-4 border-t-2 border-indigo-100">
          {user && !collapsed && (
            <div className="mb-3 px-3 py-2 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-sm font-semibold text-gray-800 truncate">{user.username}</span>
                <span className="text-xs text-indigo-600 font-bold shrink-0">{user.role}</span>
              </div>
            </div>
          )}
          <button
            onClick={onLogout}
            className={`
              w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-xl
              text-red-600 hover:bg-red-50 transition-all duration-200
              ${collapsed ? 'justify-center' : ''}
            `}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICONS.logout} />
            </svg>
            {!collapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Mobile toggle button */}
      <button
        onClick={onToggle}
        className={`
          fixed top-4 left-4 z-30 p-3 rounded-xl bg-white/90 backdrop-blur shadow-lg
          border-2 border-indigo-100 text-indigo-600 hover:bg-indigo-50 transition-all
          lg:hidden ${!collapsed ? 'hidden' : ''}
        `}
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICONS.menu} />
        </svg>
      </button>
    </>
  );
}
