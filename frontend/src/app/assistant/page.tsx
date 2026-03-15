'use client';

import { useEffect, useRef, useState } from 'react';
import MainLayout from '@/components/MainLayout';
import { assistantApi } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type MatchedEntity = {
  entity_type: string;
  id: number;
  name: string;
  npwp?: string;
  entity_subtype?: string;
  status?: string;
  nationality?: string;
  graph_url?: string;
  confidence: number;
};

type AssistantResponse = {
  query: string;
  intent: string;
  found: boolean;
  match_count: number;
  entities: MatchedEntity[];
  message: string;
  timestamp: string;
};

type Message =
  | { role: 'user'; text: string }
  | { role: 'assistant'; response: AssistantResponse }
  | { role: 'error'; text: string };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const ENTITY_ICONS: Record<string, string> = {
  TAXPAYER: '🏢',
  BENEFICIAL_OWNER: '👤',
  GROUP: '🏛️',
  OFFICER: '💼',
};

const ENTITY_COLORS: Record<string, string> = {
  TAXPAYER: 'text-blue-400',
  BENEFICIAL_OWNER: 'text-emerald-400',
  GROUP: 'text-purple-400',
  OFFICER: 'text-amber-400',
};

const CONFIDENCE_BAR = (c: number) => {
  const pct = Math.round(c * 100);
  const color =
    pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-orange-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500">{pct}%</span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Quick-suggestion chips
// ---------------------------------------------------------------------------
const SUGGESTIONS = [
  'Cari PT Sinar Jaya Abadi',
  'NPWP 01.234.567.8-000.000',
  'Apakah Andi Pratama ada di database?',
  'Tampilkan grup Indofood',
  'Cari beneficial owner WNA',
];

// ---------------------------------------------------------------------------
// Entity result card
// ---------------------------------------------------------------------------
function EntityCard({ entity }: { entity: MatchedEntity }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 flex items-start gap-3">
      <div className="text-xl shrink-0 mt-0.5">
        {ENTITY_ICONS[entity.entity_type] || '📄'}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="text-sm font-semibold text-white truncate">{entity.name}</div>
          <span className={`text-xs shrink-0 ${ENTITY_COLORS[entity.entity_type] || 'text-gray-400'}`}>
            {entity.entity_type.replace('_', ' ')}
          </span>
        </div>
        {entity.npwp && (
          <div className="text-xs text-gray-400 font-mono mt-0.5">{entity.npwp}</div>
        )}
        <div className="flex flex-wrap gap-2 mt-1">
          {entity.entity_subtype && (
            <span className="text-xs text-gray-500">{entity.entity_subtype}</span>
          )}
          {entity.status && (
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              entity.status === 'ACTIVE'
                ? 'bg-green-900/40 text-green-400'
                : 'bg-gray-700 text-gray-400'
            }`}>
              {entity.status}
            </span>
          )}
          {entity.nationality && (
            <span className="text-xs text-gray-500">🌐 {entity.nationality}</span>
          )}
        </div>
        <div className="mt-2">{CONFIDENCE_BAR(entity.confidence)}</div>
        {entity.graph_url && (
          <a
            href={entity.graph_url}
            className="inline-flex items-center gap-1 mt-2 text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            🕸️ Buka Graph Explorer →
          </a>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    const query = text.trim();
    if (!query || loading) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: query }]);
    setLoading(true);

    try {
      const res = await assistantApi.entityDiscovery(query, 5);
      setMessages((prev) => [...prev, { role: 'assistant', response: res.data }]);
    } catch {
      setMessages((prev) => [...prev, { role: 'error', text: 'Gagal menghubungi server. Coba lagi.' }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <MainLayout>
      <div className="flex flex-col h-screen bg-gray-950 text-white">
        {/* Header */}
        <div className="p-4 border-b border-gray-800 shrink-0">
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            🤖 Asisten Entitas SmartWeb
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Cari wajib pajak, beneficial owner, grup, atau pejabat menggunakan bahasa alami
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {/* Welcome message */}
          {messages.length === 0 && (
            <div className="max-w-2xl mx-auto text-center mt-8">
              <div className="text-5xl mb-4">🤖</div>
              <h2 className="text-xl font-bold text-gray-200 mb-2">Asisten Penemuan Entitas</h2>
              <p className="text-gray-400 text-sm mb-6">
                Tanyakan apakah suatu wajib pajak, beneficial owner, grup, atau pejabat
                ada di database SmartWeb. Gunakan nama, NPWP, atau deskripsi bebas.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className="text-sm bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-full px-4 py-2 text-gray-300 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chat messages */}
          {messages.map((msg, i) => {
            if (msg.role === 'user') {
              return (
                <div key={i} className="flex justify-end">
                  <div className="max-w-lg bg-blue-700 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-white">
                    {msg.text}
                  </div>
                </div>
              );
            }

            if (msg.role === 'error') {
              return (
                <div key={i} className="flex justify-start">
                  <div className="max-w-lg bg-red-900/50 border border-red-700 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm text-red-300">
                    ⚠️ {msg.text}
                  </div>
                </div>
              );
            }

            // assistant response
            const { response } = msg;
            return (
              <div key={i} className="flex justify-start">
                <div className="max-w-2xl w-full">
                  {/* Message bubble */}
                  <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="text-lg shrink-0">🤖</span>
                      <p
                        className="text-sm text-gray-200 leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: response.message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
                      />
                    </div>

                    {/* Intent badge */}
                    <div className="flex items-center gap-2 mt-1 mb-3">
                      <span className="text-xs text-gray-500">Intent:</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        response.intent === 'NPWP_SEARCH'
                          ? 'bg-blue-900/50 text-blue-300'
                          : 'bg-gray-700 text-gray-300'
                      }`}>
                        {response.intent}
                      </span>
                      <span className="text-xs text-gray-600">
                        {new Date(response.timestamp).toLocaleTimeString('id-ID')}
                      </span>
                    </div>

                    {/* Entity results */}
                    {response.entities.length > 0 && (
                      <div className="space-y-2">
                        {response.entities.map((entity, ei) => (
                          <EntityCard key={ei} entity={entity} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Loading indicator */}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex items-center gap-2 text-gray-400">
                  <span className="text-lg animate-spin">⚙️</span>
                  <span className="text-sm">Mencari entitas…</span>
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="p-4 border-t border-gray-800 shrink-0">
          <div className="max-w-3xl mx-auto flex gap-3">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Cari nama entitas atau NPWP, contoh: PT ABC atau 01.234.567.8-999.000…"
              disabled={loading}
              className="flex-1 bg-gray-800 text-white text-sm rounded-xl px-4 py-3 border border-gray-600 focus:outline-none focus:border-blue-500 placeholder-gray-500 disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={loading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold px-5 py-3 rounded-xl transition-colors"
            >
              {loading ? '⏳' : '→'}
            </button>
          </div>
          <p className="text-center text-xs text-gray-600 mt-2">
            Tekan Enter untuk mengirim · Asisten ini berbasis rule retrieval, bukan LLM
          </p>
        </div>
      </div>
    </MainLayout>
  );
}
