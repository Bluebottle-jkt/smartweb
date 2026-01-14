'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { authApi, networkApi } from '@/lib/api';
import { exportNetworkPng } from '@/lib/networkExport';

type NetworkNode = {
  id: string;
  entity_id: number;
  entity_type: string;
  entity_subtype?: string | null;
  name: string;
  location_label: string;
  layer: number;
};

type NetworkEdge = {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  label: string;
  layer: number;
};

type GraphResponse = {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  depth: number;
  year: number;
  max_nodes: number;
  truncated: boolean;
  layer_counts: Record<number, number>;
};

type ExportOptions = {
  filename: string;
  scale: number;
  includeLegend: boolean;
  area: 'canvas' | 'view';
};

type LegendCounts = Record<number, number>;

const DEFAULT_YEAR = 2024;

const nodeTypeStyles: Record<string, { label: string; color: string }> = {
  TAXPAYER: { label: 'WP', color: 'bg-blue-600 text-white' },
  BENEFICIAL_OWNER: { label: 'BO', color: 'bg-emerald-600 text-white' },
};

function NetworkNodeCard({ data }: { data: NetworkNode }) {
  const style = nodeTypeStyles[data.entity_type] || {
    label: 'EN',
    color: 'bg-gray-500 text-white',
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm px-3 py-2 min-w-[200px]">
      <div className="flex items-center gap-2">
        <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-semibold ${style.color}`}>
          {style.label}
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-900">{data.name}</div>
          {data.entity_subtype && (
            <div className="text-xs text-gray-500">{data.entity_subtype}</div>
          )}
        </div>
      </div>
      <div className="mt-2 text-xs text-gray-500">{data.location_label}</div>
      <div className="mt-1 text-[11px] text-gray-400">L{data.layer}</div>
    </div>
  );
}

function LayerIndicator({ data }: { data: { layer: number } }) {
  return (
    <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-4 py-2 rounded-full shadow-md border-2 border-blue-300">
      <div className="text-sm font-bold">Layer {data.layer}</div>
      <div className="text-[10px] opacity-90">Depth Level</div>
    </div>
  );
}

function LayerLegend({
  depth,
  counts,
  visibleLayers,
  onToggle,
}: {
  depth: number;
  counts: LegendCounts;
  visibleLayers: Set<number>;
  onToggle: (layer: number) => void;
}) {
  const layers = Array.from({ length: depth + 1 }, (_, idx) => idx);

  return (
    <div className="glass-panel p-3 space-y-2" data-export-legend="true">
      <div className="text-xs font-semibold text-gray-700">Layer Legend</div>
      <div className="flex flex-wrap gap-2">
        {layers.map((layer) => {
          const isActive = visibleLayers.has(layer);
          return (
            <button
              key={layer}
              type="button"
              onClick={() => onToggle(layer)}
              className={`px-2 py-1 rounded-full text-xs border ${
                isActive
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'bg-white text-gray-600 border-gray-300'
              }`}
            >
              L{layer} ({counts[layer] ?? 0})
            </button>
          );
        })}
      </div>
    </div>
  );
}

function NetworkPageContent() {
  const router = useRouter();
  const viewRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const [rootType, setRootType] = useState<'TAXPAYER' | 'BENEFICIAL_OWNER'>('TAXPAYER');
  const [rootId, setRootId] = useState('');
  const [year, setYear] = useState(DEFAULT_YEAR);
  const [depth, setDepth] = useState(2);
  const [maxNodes, setMaxNodes] = useState(300);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [allNodes, setAllNodes] = useState<NetworkNode[]>([]);
  const [allEdges, setAllEdges] = useState<NetworkEdge[]>([]);
  const [layerCounts, setLayerCounts] = useState<LegendCounts>({});
  const [visibleLayers, setVisibleLayers] = useState<Set<number>>(new Set([0, 1, 2]));
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [truncated, setTruncated] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    filename: 'network.png',
    scale: 2,
    includeLegend: false,
    area: 'canvas',
  });

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

  useEffect(() => {
    if (!toast) return;
    const timeout = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(timeout);
  }, [toast]);

  const canLoad = rootId.trim().length > 0 && Number(rootId) > 0 && !!year;

  const buildFilename = useCallback(() => {
    const trimmed = rootId.trim();
    if (!trimmed) return 'network.png';
    return `network_${rootType}_${trimmed}_${year}_d${depth}.png`;
  }, [rootId, rootType, year, depth]);

  useEffect(() => {
    setExportOptions((prev) => ({ ...prev, filename: buildFilename() }));
  }, [buildFilename]);

  const resetVisibleLayers = useCallback((nextDepth: number) => {
    const nextLayers = new Set<number>();
    for (let i = 0; i <= nextDepth; i += 1) {
      nextLayers.add(i);
    }
    setVisibleLayers(nextLayers);
  }, []);

  const fetchGraph = useCallback(async () => {
    if (!canLoad) {
      setError('Root, tahun, dan parameter lainnya harus diisi.');
      return;
    }
    setIsLoadingGraph(true);
    setError('');

    try {
      const response = await networkApi.graph({
        root_type: rootType,
        root_id: Number(rootId),
        year,
        depth,
        max_nodes: maxNodes,
      });
      const data: GraphResponse = response.data;
      setAllNodes(data.nodes);
      setAllEdges(data.edges);
      setLayerCounts(data.layer_counts ?? {});
      setTruncated(data.truncated);
      resetVisibleLayers(data.depth);
    } catch (err: any) {
      console.error('Network graph error:', err);
      let errorMessage = 'Gagal memuat graph jaringan.';

      if (err.response?.data) {
        const errorData = err.response.data;
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        } else if (errorData.detail && typeof errorData.detail === 'object') {
          errorMessage = JSON.stringify(errorData.detail);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
    } finally {
      setIsLoadingGraph(false);
    }
  }, [canLoad, rootType, rootId, year, depth, maxNodes, resetVisibleLayers]);

  useEffect(() => {
    if (!autoRefresh) return;
    if (!canLoad) return;
    fetchGraph();
  }, [autoRefresh, canLoad, fetchGraph]);

  const toggleLayer = useCallback((layer: number) => {
    setVisibleLayers((prev) => {
      const next = new Set(prev);
      if (next.has(layer)) {
        next.delete(layer);
      } else {
        next.add(layer);
      }
      return next;
    });
  }, []);

  const layoutNodes = useCallback((nodes: NetworkNode[]) => {
    const grouped = nodes.reduce<Record<number, NetworkNode[]>>((acc, node) => {
      acc[node.layer] = acc[node.layer] || [];
      acc[node.layer].push(node);
      return acc;
    }, {});

    const sortedLayers = Object.keys(grouped)
      .map((value) => Number(value))
      .sort((a, b) => a - b);

    const positioned = [];
    const columnWidth = 380;
    const rowHeight = 140;
    const layerLabelOffset = -80;

    for (const layer of sortedLayers) {
      const layerNodes = grouped[layer];
      layerNodes.sort((a, b) => a.name.localeCompare(b.name));

      // Add depth layer indicator node
      positioned.push({
        id: `layer-${layer}`,
        type: 'layerIndicator',
        data: { layer },
        position: { x: layer * columnWidth, y: layerLabelOffset },
        draggable: false,
        selectable: false,
      });

      // Position entity nodes
      layerNodes.forEach((node, index) => {
        positioned.push({
          id: node.id,
          type: 'networkNode',
          data: node,
          position: { x: layer * columnWidth, y: index * rowHeight },
        });
      });
    }

    return positioned;
  }, []);

  const flowNodes = useMemo(() => layoutNodes(allNodes), [allNodes, layoutNodes]);
  const flowEdges = useMemo(() => {
    return allEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 20,
        height: 20,
        color: '#3b82f6',
      },
      type: 'smoothstep',
      animated: true,
      style: {
        strokeWidth: 2.5,
        stroke: '#3b82f6',
      },
      labelStyle: {
        fontSize: 12,
        fontWeight: 700,
        fill: '#1f2937',
        background: '#ffffff',
        padding: '4px 8px',
        borderRadius: '4px',
        border: '1px solid #3b82f6',
      },
      labelBgStyle: {
        fill: '#ffffff',
        fillOpacity: 0.95,
      },
      labelBgPadding: [8, 4] as [number, number],
      labelBgBorderRadius: 4,
    }));
  }, [allEdges]);

  const filteredNodes = useMemo(() => {
    if (visibleLayers.size === 0) return [];
    return flowNodes.filter((node) => {
      // Always show layer indicators
      if (node.type === 'layerIndicator') return true;
      // Filter entity nodes by layer visibility
      return visibleLayers.has(node.data.layer);
    });
  }, [flowNodes, visibleLayers]);

  const filteredEdges = useMemo(() => {
    const allowed = new Set(filteredNodes.map((node) => node.id));
    return flowEdges.filter((edge) => allowed.has(edge.source) && allowed.has(edge.target));
  }, [filteredNodes, flowEdges]);

  const handleExport = useCallback(async () => {
    const target = exportOptions.area === 'view' ? viewRef.current : canvasRef.current;
    if (!target) {
      setToast({ type: 'error', message: 'Target export tidak ditemukan.' });
      return;
    }

    try {
      await exportNetworkPng({
        element: target,
        filename: exportOptions.filename,
        scale: exportOptions.scale,
        includeLegend: exportOptions.includeLegend,
      });
      setToast({ type: 'success', message: 'PNG berhasil diunduh.' });
      setExportOpen(false);
    } catch (err) {
      setToast({ type: 'error', message: 'Gagal mengekspor PNG.' });
    }
  }, [exportOptions]);

  if (userLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen" ref={viewRef}>
      <header className="bg-white/70 backdrop-blur border-b border-white/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <button onClick={() => router.push('/')} className="btn-secondary mb-2">← Beranda</button>
              <h1 className="text-2xl font-bold text-gray-900">Network Graph</h1>
              <p className="text-sm text-gray-600">Visualisasi jaringan WP dan Beneficial Owner</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setExportOpen(true)}
                className="btn-primary text-sm"
              >
                Export PNG
              </button>
              <span className="text-sm text-gray-700">
                {user.username} ({user.role})
              </span>
              <button
                onClick={async () => {
                  await authApi.logout();
                  router.push('/login');
                }}
                className="btn-secondary text-sm"
              >
                Keluar
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <section className="glass-panel p-4">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Root Type</label>
              <select
                className="input-field"
                value={rootType}
                onChange={(event) => setRootType(event.target.value as 'TAXPAYER' | 'BENEFICIAL_OWNER')}
              >
                <option value="TAXPAYER">Taxpayer</option>
                <option value="BENEFICIAL_OWNER">Beneficial Owner</option>
              </select>
            </div>
            <div style={{ position: 'relative', zIndex: 10 }}>
              <label htmlFor="rootIdInput" className="block text-xs font-semibold text-gray-600 mb-1">Root ID</label>
              <input
                id="rootIdInput"
                name="rootId"
                className="input-field"
                type="text"
                value={rootId}
                onChange={(e) => setRootId(e.target.value)}
                placeholder="Ketik ID disini..."
                style={{ cursor: 'text', userSelect: 'text', WebkitUserSelect: 'text' }}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Tahun</label>
              <select
                className="input-field"
                value={year}
                onChange={(event) => setYear(Number(event.target.value))}
              >
                {[2022, 2023, 2024, 2025].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Depth</label>
              <select
                className="input-field"
                value={depth}
                onChange={(event) => setDepth(Number(event.target.value))}
              >
                {[1, 2, 3, 4, 5].map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Max Nodes</label>
              <input
                className="input-field"
                type="number"
                min={50}
                max={1500}
                value={maxNodes}
                onChange={(event) => setMaxNodes(Number(event.target.value))}
              />
            </div>
            <div className="flex items-end gap-3">
              <button
                onClick={fetchGraph}
                className="btn-primary w-full"
                disabled={!canLoad || isLoadingGraph}
              >
                {isLoadingGraph ? 'Memuat...' : 'Load Graph'}
              </button>
              <label className="flex items-center gap-2 text-xs text-gray-600">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(event) => setAutoRefresh(event.target.checked)}
                />
                Auto-refresh
              </label>
            </div>
          </div>

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">
              {error}
            </div>
          )}
          {truncated && (
            <div className="mt-3 text-xs text-amber-600">
              Hasil dipotong karena melebihi batas node. Kurangi depth atau max nodes.
            </div>
          )}
        </section>

        <section className="relative glass-panel">
          <div className="absolute right-4 top-4 z-10">
            <LayerLegend
              depth={depth}
              counts={layerCounts}
              visibleLayers={visibleLayers}
              onToggle={toggleLayer}
            />
          </div>
          <div ref={canvasRef} className="h-[680px] bg-white/90 rounded-2xl">
            {filteredNodes.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center space-y-4 max-w-md">
                  <div className="text-gray-400">
                    <svg className="w-24 h-24 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-700">Belum Ada Data Graph</h3>
                  <p className="text-sm text-gray-600">
                    Masukkan <strong>Root ID</strong> (contoh: 12 untuk Taxpayer, atau 1 untuk Beneficial Owner),
                    pilih <strong>Tahun</strong> dan <strong>Depth</strong>, lalu klik <strong>Load Graph</strong> untuk memvisualisasikan jaringan.
                  </p>
                  <div className="pt-2">
                    <button
                      onClick={() => {
                        setRootType('TAXPAYER');
                        setRootId('12');
                        setYear(2024);
                        setDepth(2);
                        setTimeout(() => fetchGraph(), 100);
                      }}
                      className="btn-primary text-sm"
                    >
                      Muat Contoh Data (Taxpayer #12)
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <ReactFlow
                nodes={filteredNodes}
                edges={filteredEdges}
                nodeTypes={{
                  networkNode: NetworkNodeCard,
                  layerIndicator: LayerIndicator,
                }}
                fitView
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable
              >
                <MiniMap />
                <Controls />
                <Background />
              </ReactFlow>
            )}
          </div>
        </section>
      </main>

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 export-hide">
          <div
            className={`px-4 py-2 rounded shadow text-sm ${
              toast.type === 'success'
                ? 'bg-green-600 text-white'
                : 'bg-red-600 text-white'
            }`}
          >
            {toast.message}
          </div>
        </div>
      )}

      {exportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 export-hide">
          <div className="bg-white rounded-lg shadow-lg w-full max-w-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Export PNG</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Filename</label>
                <input
                  className="input-field"
                  value={exportOptions.filename}
                  onChange={(event) => setExportOptions((prev) => ({
                    ...prev,
                    filename: event.target.value,
                  }))}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Resolution Scale</label>
                <select
                  className="input-field"
                  value={exportOptions.scale}
                  onChange={(event) => setExportOptions((prev) => ({
                    ...prev,
                    scale: Number(event.target.value),
                  }))}
                >
                  {[1, 2, 3].map((scale) => (
                    <option key={scale} value={scale}>{scale}x</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Area</label>
                <select
                  className="input-field"
                  value={exportOptions.area}
                  onChange={(event) => setExportOptions((prev) => ({
                    ...prev,
                    area: event.target.value as ExportOptions['area'],
                  }))}
                >
                  <option value="canvas">Export Canvas PNG</option>
                  <option value="view">Export View PNG</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={exportOptions.includeLegend}
                  onChange={(event) => setExportOptions((prev) => ({
                    ...prev,
                    includeLegend: event.target.checked,
                  }))}
                />
                Include legend
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                className="btn-secondary"
                onClick={() => setExportOpen(false)}
              >
                Batal
              </button>
              <button
                className="btn-primary"
                onClick={handleExport}
              >
                Export
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function NetworkPage() {
  return (
    <ReactFlowProvider>
      <NetworkPageContent />
    </ReactFlowProvider>
  );
}
