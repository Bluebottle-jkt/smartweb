'use client';

import { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

interface MenuItem {
  label: string;
  path?: string;
  icon?: React.ReactNode;
  children?: MenuItem[];
  defaultExpanded?: boolean;
}

interface SidebarProps {
  user: { username: string; role: string } | null;
  onLogout: () => void;
  collapsed?: boolean;
  onToggle?: () => void;
}

// Icons as components
const MapIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
  </svg>
);

const ExploreIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16l2.879-2.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const OwnershipIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
  </svg>
);

const CompanyIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
  </svg>
);

const StructureIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
  </svg>
);

const BOIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const GroupIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
  </svg>
);

const ControllerIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const SubsidiaryIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
  </svg>
);

const FamilyIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
);

const DirectorIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

const TransactionIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
  </svg>
);

const NetworkIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
  </svg>
);

const ChevronDownIcon = ({ open }: { open: boolean }) => (
  <svg
    className={`w-4 h-4 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const LogoutIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
);

const MenuToggleIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
);

const menuItems: MenuItem[] = [
  {
    label: 'Peta Sebaran Group',
    path: '/peta-sebaran',
    icon: <MapIcon />,
  },
  {
    label: 'Explorasi Manual',
    path: '/explorasi-manual',
    icon: <ExploreIcon />,
  },
  {
    label: 'Pencarian NPWP',
    path: '/pencarian-npwp',
    icon: <SearchIcon />,
  },
  {
    label: 'Kepemilikan',
    icon: <OwnershipIcon />,
    defaultExpanded: true,
    children: [
      { label: 'Perusahaan', path: '/kepemilikan/perusahaan', icon: <CompanyIcon /> },
      { label: 'Struktur Kepemilikan', path: '/kepemilikan/struktur', icon: <StructureIcon /> },
      { label: 'Beneficial Owner', path: '/kepemilikan/beneficial-owner', icon: <BOIcon /> },
      { label: 'Group', path: '/kepemilikan/group', icon: <GroupIcon /> },
      { label: 'Pengendali', path: '/kepemilikan/pengendali', icon: <ControllerIcon /> },
      { label: 'Anak Usaha', path: '/kepemilikan/anak-usaha', icon: <SubsidiaryIcon /> },
      { label: 'Keluarga Pemegang Saham', path: '/kepemilikan/keluarga', icon: <FamilyIcon /> },
      { label: 'Group Pengurus', path: '/kepemilikan/pengurus', icon: <DirectorIcon /> },
    ],
  },
  {
    label: 'Transaksi Bisnis',
    path: '/transaksi-bisnis',
    icon: <TransactionIcon />,
  },
  {
    label: 'Group',
    path: '/group-menu',
    icon: <GroupIcon />,
  },
  {
    label: 'Jaringan Wajib Pajak',
    path: '/jaringan-wp',
    icon: <NetworkIcon />,
  },
];

export default function Sidebar({ user, onLogout, collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [expandedSections, setExpandedSections] = useState<string[]>(['Kepemilikan']);

  const toggleSection = (label: string) => {
    setExpandedSections((prev) =>
      prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label]
    );
  };

  const isActive = (path?: string) => {
    if (!path) return false;
    return pathname === path || pathname.startsWith(path + '/');
  };

  const renderMenuItem = (item: MenuItem, depth = 0) => {
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedSections.includes(item.label);
    const active = isActive(item.path);

    return (
      <div key={item.label}>
        <button
          onClick={() => {
            if (hasChildren) {
              toggleSection(item.label);
            } else if (item.path) {
              router.push(item.path);
            }
          }}
          className={`
            w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200
            ${depth > 0 ? 'ml-4 pl-6' : ''}
            ${active
              ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg'
              : 'text-gray-700 hover:bg-indigo-50 hover:text-indigo-600'
            }
          `}
        >
          <span className={`${active ? 'text-white' : 'text-indigo-500'}`}>
            {item.icon}
          </span>
          {!collapsed && (
            <>
              <span className="flex-1 text-left">{item.label}</span>
              {hasChildren && <ChevronDownIcon open={isExpanded} />}
            </>
          )}
        </button>

        {hasChildren && isExpanded && !collapsed && (
          <div className="mt-1 space-y-1">
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
              <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 shadow-lg flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              {!collapsed && (
                <div>
                  <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                    Menu Group
                  </h1>
                  <p className="text-xs text-gray-500">Task Force WP Grup</p>
                </div>
              )}
            </div>
            <button
              onClick={onToggle}
              className="p-2 rounded-lg hover:bg-indigo-50 text-gray-600 hover:text-indigo-600 transition-colors lg:hidden"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Menu Items */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-2">
          {menuItems.map((item) => renderMenuItem(item))}
        </nav>

        {/* User & Logout */}
        <div className="p-4 border-t-2 border-indigo-100">
          {user && !collapsed && (
            <div className="mb-3 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-sm font-semibold text-gray-800">{user.username}</span>
                <span className="text-xs text-indigo-600 font-bold">{user.role}</span>
              </div>
            </div>
          )}
          <button
            onClick={onLogout}
            className={`
              w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl
              text-red-600 hover:bg-red-50 transition-all duration-200
              ${collapsed ? 'justify-center' : ''}
            `}
          >
            <LogoutIcon />
            {!collapsed && <span>Logout → {user?.username || 'User'}</span>}
          </button>
        </div>
      </aside>

      {/* Toggle button for mobile */}
      <button
        onClick={onToggle}
        className={`
          fixed top-4 left-4 z-30 p-3 rounded-xl bg-white/90 backdrop-blur shadow-lg
          border-2 border-indigo-100 text-indigo-600 hover:bg-indigo-50 transition-all
          lg:hidden
          ${!collapsed ? 'hidden' : ''}
        `}
      >
        <MenuToggleIcon />
      </button>
    </>
  );
}