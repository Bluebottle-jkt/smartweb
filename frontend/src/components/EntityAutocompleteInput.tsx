'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { entitiesApi } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type EntitySuggestion = {
  entity_type: 'TAXPAYER' | 'BENEFICIAL_OWNER' | 'GROUP' | 'OFFICER';
  id: number;
  name: string;
  npwp_masked?: string;
  subtitle?: string;
  entity_subtype?: string;
  city?: string;
  kpp_name?: string;
  kanwil_name?: string;
  rank?: number;
};

type Props = {
  value?: string;
  onChange?: (value: string) => void;
  onSelect?: (entity: EntitySuggestion) => void;
  placeholder?: string;
  label?: string;
  required?: boolean;
  className?: string;
  entityTypes?: string[];   // filter by entity type(s)
  disabled?: boolean;
};

// ---------------------------------------------------------------------------
// Icon per entity type
// ---------------------------------------------------------------------------
const ENTITY_ICONS: Record<string, string> = {
  TAXPAYER:        '🏢',
  BENEFICIAL_OWNER:'👤',
  GROUP:           '🏛️',
  OFFICER:         '💼',
};

const ENTITY_COLOURS: Record<string, string> = {
  TAXPAYER:        'text-blue-400',
  BENEFICIAL_OWNER:'text-emerald-400',
  GROUP:           'text-purple-400',
  OFFICER:         'text-amber-400',
};

// ---------------------------------------------------------------------------
// Debounce hook
// ---------------------------------------------------------------------------
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState<T>(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function EntityAutocompleteInput({
  value: controlledValue,
  onChange: controlledOnChange,
  onSelect,
  placeholder = 'Cari nama atau NPWP...',
  label,
  required = false,
  className = '',
  entityTypes,
  disabled = false,
}: Props) {
  const [internalValue, setInternalValue] = useState('');
  const value = controlledValue !== undefined ? controlledValue : internalValue;
  const onChange = useCallback((v: string) => {
    controlledOnChange?.(v);
    if (controlledValue === undefined) setInternalValue(v);
  }, [controlledOnChange, controlledValue]);

  const [suggestions, setSuggestions] = useState<EntitySuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const debouncedValue = useDebounce(value, 220);

  // Fetch suggestions whenever debounced value changes
  useEffect(() => {
    if (!debouncedValue || debouncedValue.length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    entitiesApi
      .suggest(debouncedValue, 8, entityTypes)
      .then((res) => {
        if (cancelled) return;
        setSuggestions(res.data || []);
        setOpen(true);
        setActiveIdx(-1);
      })
      .catch(() => {
        if (!cancelled) setSuggestions([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [debouncedValue, entityTypes]);

  const handleSelect = useCallback(
    (entity: EntitySuggestion) => {
      const display = entity.npwp_masked
        ? `${entity.name} (${entity.npwp_masked})`
        : entity.name;
      onChange(entity.npwp_masked || entity.name);
      setSuggestions([]);
      setOpen(false);
      setActiveIdx(-1);
      onSelect?.(entity);
    },
    [onChange, onSelect]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (!open || suggestions.length === 0) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, -1));
      } else if (e.key === 'Enter' && activeIdx >= 0) {
        e.preventDefault();
        handleSelect(suggestions[activeIdx]);
      } else if (e.key === 'Escape') {
        setOpen(false);
        setActiveIdx(-1);
      }
    },
    [open, suggestions, activeIdx, handleSelect]
  );

  // Scroll active item into view
  useEffect(() => {
    if (activeIdx >= 0 && listRef.current) {
      const item = listRef.current.children[activeIdx] as HTMLElement;
      item?.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIdx]);

  return (
    <div className={`relative ${className}`}>
      {label && (
        <label className="block text-xs text-gray-400 mb-1">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
      )}

      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          className="
            w-full bg-gray-800 text-white text-sm rounded px-3 py-2 pr-8
            border border-gray-600 focus:outline-none focus:border-blue-500
            placeholder-gray-500 disabled:opacity-50
          "
        />
        {/* Loading spinner / clear icon */}
        <div className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500">
          {loading ? (
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          ) : value ? (
            <button
              type="button"
              onClick={() => { onChange(''); setSuggestions([]); setOpen(false); }}
              className="hover:text-gray-300"
            >
              ✕
            </button>
          ) : (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
        </div>
      </div>

      {/* Dropdown */}
      {open && suggestions.length > 0 && (
        <ul
          ref={listRef}
          className="
            absolute z-50 w-full mt-1 max-h-64 overflow-y-auto
            bg-gray-800 border border-gray-600 rounded-lg shadow-xl
          "
        >
          {suggestions.map((s, i) => (
            <li key={`${s.entity_type}-${s.id}`}>
              <button
                type="button"
                onMouseDown={() => handleSelect(s)}
                className={`
                  w-full text-left px-3 py-2.5 flex items-start gap-2.5 transition-colors
                  ${i === activeIdx ? 'bg-blue-800' : 'hover:bg-gray-700'}
                `}
              >
                <span className="text-lg shrink-0 mt-0.5">{ENTITY_ICONS[s.entity_type] || '📄'}</span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-white font-medium truncate">{s.name}</div>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    {s.npwp_masked && (
                      <span className="text-xs text-gray-400 font-mono">{s.npwp_masked}</span>
                    )}
                    {s.entity_subtype && (
                      <span className="text-xs text-gray-500">{s.entity_subtype}</span>
                    )}
                    {s.city && (
                      <span className="text-xs text-gray-500">📍 {s.city}</span>
                    )}
                    {s.kpp_name && (
                      <span className="text-xs text-gray-500">KPP {s.kpp_name}</span>
                    )}
                  </div>
                </div>
                <span className={`text-xs shrink-0 mt-1 ${ENTITY_COLOURS[s.entity_type] || 'text-gray-400'}`}>
                  {s.entity_type.replace('_', ' ')}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* No results */}
      {open && !loading && value.length >= 2 && suggestions.length === 0 && (
        <div className="
          absolute z-50 w-full mt-1 bg-gray-800 border border-gray-600
          rounded-lg shadow-xl px-3 py-3 text-sm text-gray-400
        ">
          Tidak ada hasil untuk &ldquo;{value}&rdquo;
        </div>
      )}
    </div>
  );
}
