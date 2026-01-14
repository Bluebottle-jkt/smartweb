'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchApi } from '@/lib/api';
import { useRouter } from 'next/navigation';

interface SearchResult {
  entity_type: 'GROUP' | 'TAXPAYER' | 'BENEFICIAL_OWNER';
  id: number;
  name: string;
  subtitle: string;
  rank: number;
}

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const { data: suggestions = [], isLoading } = useQuery({
    queryKey: ['search-suggest', query],
    queryFn: async () => {
      if (query.length < 2) return [];
      const response = await searchApi.suggest(query, 10);
      return response.data as SearchResult[];
    },
    enabled: query.length >= 2,
  });

  useEffect(() => {
    setIsOpen(suggestions.length > 0);
    setSelectedIndex(0);
  }, [suggestions]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (item: SearchResult) => {
    const paths: Record<string, string> = {
      'GROUP': '/groups',
      'TAXPAYER': '/taxpayers',
      'BENEFICIAL_OWNER': '/beneficial-owners',
    };
    router.push(`${paths[item.entity_type]}/${item.id}`);
    setIsOpen(false);
    setQuery('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && suggestions[selectedIndex]) {
      e.preventDefault();
      handleSelect(suggestions[selectedIndex]);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'GROUP': 'Grup',
      'TAXPAYER': 'Wajib Pajak',
      'BENEFICIAL_OWNER': 'Beneficial Owner',
    };
    return labels[type] || type;
  };

  return (
    <div ref={wrapperRef} className="relative w-full max-w-3xl">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Cari nama Grup, Wajib Pajak, atau Beneficial Owner..."
          className="input-field text-lg py-3 pr-12 shadow-lg"
        />
        {isLoading && (
          <div className="absolute right-3 top-3.5">
            <div className="animate-spin h-5 w-5 border-2 border-primary-500 border-t-transparent rounded-full" />
          </div>
        )}
      </div>

      {isOpen && suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-3 bg-white/90 backdrop-blur border border-white/70 rounded-2xl shadow-xl max-h-96 overflow-y-auto">
          {suggestions.map((item, index) => (
            <button
              key={`${item.entity_type}-${item.id}`}
              onClick={() => handleSelect(item)}
              className={`w-full text-left px-4 py-3 hover:bg-white border-b border-white/60 last:border-b-0 ${
                index === selectedIndex ? 'bg-white/80' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{item.name}</div>
                  <div className="text-sm text-gray-500">{item.subtitle}</div>
                </div>
                <span className="ml-2 px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded">
                  {getTypeLabel(item.entity_type)}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
