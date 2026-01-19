'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
} from 'reactflow';
import 'reactflow/dist/style.css';

import MainLayout from '@/components/MainLayout';
import { authApi, networkApi, searchApi } from '@/lib/api';
import { exportNetworkPng } from '@/lib/networkExport';

// Types
type NetworkNode = {
  id: string;
  entity_id: number;
  entity_type: string;
  entity_subtype?: string | null;
  name: string;
  npwp?: string;
  location_label: string;
  layer: number;
  category?: 'Entity' | 'Officer' | 'Address' | 'Intermediary';
};

type NetworkEdge = {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  label: string;
  layer: number;
  pct?: number;
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

// Category colors and styles (ICIJ-like)
const categoryStyles: Record<string, { bg: string; text: string; border: string; icon: string }> = {
  Entity: {
    bg: 'bg-blue-500',
    text: 'text-white',
    border: 'border-blue-400',
    icon: '🏢',
  },
  Officer: {
    bg: 'bg-emerald-500',
    text: 'text-white',
    border: 'border-emerald-400',
    icon: '👤',
  },
  Address: {
    bg: 'bg-amber-500',
    text: 'text-white',
    border: 'border-amber-400',
    icon: '📍',
  },
  Intermediary: {
    bg: 'bg-purple-500',
    text: 'text-white',
    border: 'border-purple-400',
    icon: '🔗',
  },
  TAXPAYER: {
    bg: 'bg-blue-600',
    text: 'text-white',
    border: 'border-blue-400',
    icon: '🏢',
  },
  BENEFICIAL_OWNER: {
    bg: 'bg-emerald-600',
    text: 'text-white',
    border: 'border-emerald-400',
    icon: '👤',
  },
};

// Edge type options
const edgeTypeOptions = [
  { value: 'OWNERSHIP', label: 'Kepemilikan', color: '#3b82f6' },
  { value: 'CONTROL', label: 'Pengendalian', color: '#8b5cf6' },
  { value: 'FAMILY', label: 'Keluarga', color: '#ec4899' },
  { value: 'AFFILIATION_OTHER', label: 'Afiliasi Lain', color: '#f59e0b' },
];

// Network Node Component (ICIJ-like)
function NetworkNodeCard({ data, selected }: { data: NetworkNode & { isLoading?: boolean; onDoubleClick?: () => void }; selected?: boolean }) {
  const category = data.category || data.entity_type;
  const style = categoryStyles[category] || categoryStyles.Entity;

  return (
    <div
      className={`
        relative rounded-xl border-2 bg-white shadow-lg px-4 py-3 min-w-[220px] max-w-[280px]
        transition-all duration-200 cursor-pointer
        ${selected ? 'ring-4 ring-indigo-400 shadow-xl scale-105' : 'hover:shadow-xl hover:scale-102'}
        ${style.border}
      `}
      onDoubleClick={data.onDoubleClick}
    >
      {/* Loading overlay */}
      {data.isLoading && (
        <div className="absolute inset-0 bg-white/80 rounded-xl flex items-center justify-center z-10">
          <div className="animate-spin h-6 w-6 border-2 border-indigo-600 border-t-transparent rounded-full" />
        </div>
      )}

      {/* Header with icon */}
      <div className="flex items-start gap-3">
        <div className={`h-10 w-10 rounded-full flex items-center justify-center text-lg ${style.bg} ${style.text} shadow-md flex-shrink-0`}>
          {style.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-gray-900 truncate" title={data.name}>
            {data.name}
          </div>
          {data.npwp && (
            <div className="text-xs text-gray-500 font-mono truncate" title={data.npwp}>
              {data.npwp}
            </div>
          )}
          <div className="text-xs text-gray-400 mt-1">
            {data.entity_subtype || category}
          </div>
        </div>
      </div>

      {/* Location */}
      <div className="mt-2 pt-2 border-t border-gray-100">
        <div className="text-xs text-gray-500 flex items-center gap-1">
          <span>📍</span>
          <span className="truncate">{data.location_label || 'Indonesia'}</span>
        </div>
      </div>

      {/* Layer badge */}
      <div className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center shadow">
        {data.layer}
      </div>
    </div>
  );
}

// Category Legend Component
function CategoryLegend({ onCategoryToggle, visibleCategories }: {
  onCategoryToggle: (category: string) => void;
  visibleCategories: Set<string>;
}) {
  const categories = Object.entries(categoryStyles).filter(([key]) =>
    ['Entity', 'Officer', 'Address', 'Intermediary', 'TAXPAYER', 'BENEFICIAL_OWNER'].includes(key)
  );

  return (
    <div className="glass-panel p-4 space-y-3">
      <div className="text-xs font-bold text-gray-700 uppercase tracking-wide">Kategori</div>
      <div className="space-y-2">
        {categories.map(([key, style]) => (
          <button
            key={key}
            onClick={() => onCategoryToggle(key)}
            className={`
              flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-all
              ${visibleCategories.has(key) ? 'bg-gray-100' : 'bg-gray-50 opacity-50'}
            `}
          >
            <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs ${style.bg} ${style.text}`}>
              {style.icon}
            </div>
            <span className="text-gray-700 font-medium">{key === 'TAXPAYER' ? 'Wajib Pajak' : key === 'BENEFICIAL_OWNER' ? 'Beneficial Owner' : key}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// Node Detail Popover
function NodeDetailPopover({ node, onClose, connections }: {
  node: NetworkNode | null;
  onClose: () => void;
  connections: number;
}) {
  if (!node) return null;

  const category = node.category || node.entity_type;
  const style = categoryStyles[category] || categoryStyles.Entity;

  return (
    <div className="absolute top-4 right-4 z-50 glass-panel p-4 w-80 shadow-2xl">
      <button
        onClick={onClose}
        className="absolute top-2 right-2 p-1 hover:bg-gray-100 rounded"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <div className="flex items-center gap-3 mb-4">
        <div className={`h-12 w-12 rounded-full flex items-center justify-center text-xl ${style.bg} ${style.text}`}>
          {style.icon}
        </div>
        <div>
          <div className="font-bold text-gray-900">{node.name}</div>
          <div className="text-xs text-gray-500">{category}</div>
        </div>
      </div>

      <div className="space-y-2 text-sm">
        {node.npwp && (
          <div className="flex justify-between">
            <span className="text-gray-500">NPWP:</span>
            <span className="font-mono text-gray-900">{node.npwp}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-gray-500">Location:</span>
          <span className="text-gray-900">{node.location_label || 'Indonesia'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Layer:</span>
          <span className="text-gray-900">{node.layer}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Connections:</span>
          <span className="font-bold text-indigo-600">{connections}</span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Double-click node untuk memperluas jaringan
        </p>
      </div>
    </div>
  );
}

function JaringanWPContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const viewRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  // URL params
  const initialNpwp = searchParams.get('npwp') || '';
  const initialYear = searchParams.get('year') || '2024';

  // State
  const [npwp, setNpwp] = useState(initialNpwp);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [year, setYear] = useState(Number(initialYear));
  const [depth, setDepth] = useState(2);
  const [maxNodes, setMaxNodes] = useState(300);
  const [selectedEdgeTypes, setSelectedEdgeTypes] = useState<string[]>(['OWNERSHIP', 'CONTROL', 'FAMILY', 'AFFILIATION_OTHER']);
  const [isLoading, setIsLoading] = useState(false);
  const [expandingNodeId, setExpandingNodeId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [truncated, setTruncated] = useState(false);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [visibleCategories, setVisibleCategories] = useState<Set<string>>(new Set(['Entity', 'Officer', 'Address', 'Intermediary', 'TAXPAYER', 'BENEFICIAL_OWNER']));

  // Graph state with ReactFlow hooks
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Store for deduplication
  const nodeStore = useRef<Map<string, NetworkNode>>(new Map());
  const edgeStore = useRef<Map<string, NetworkEdge>>(new Map());

  // Auth check
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

  // Load initial graph if NPWP provided
  useEffect(() => {
    if (initialNpwp && user) {
      handleSearch();
    }
  }, [initialNpwp, user]);

  // Convert stored nodes/edges to ReactFlow format
  const updateFlowFromStore = useCallback(() => {
    const allNodes = Array.from(nodeStore.current.values());
    const allEdges = Array.from(edgeStore.current.values());

    // Layout nodes by layer
    const grouped = allNodes.reduce<Record<number, NetworkNode[]>>((acc, node) => {
      acc[node.layer] = acc[node.layer] || [];
      acc[node.layer].push(node);
      return acc;
    }, {});

    const sortedLayers = Object.keys(grouped).map(Number).sort((a, b) => a - b);
    const columnWidth = 350;
    const rowHeight = 160;

    const flowNodes: Node[] = [];
    for (const layer of sortedLayers) {
      const layerNodes = grouped[layer];
      layerNodes.sort((a, b) => a.name.localeCompare(b.name));

      layerNodes.forEach((node, index) => {
        flowNodes.push({
          id: node.id,
          type: 'networkNode',
          data: {
            ...node,
            isLoading: expandingNodeId === node.id,
            onDoubleClick: () => handleNodeExpand(node),
          },
          position: { x: layer * columnWidth, y: index * rowHeight },
        });
      });
    }

    const flowEdges: Edge[] = allEdges.map((edge) => {
      const edgeType = edgeTypeOptions.find(e => e.value === edge.relationship_type);
      const color = edgeType?.color || '#6b7280';

      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label + (edge.pct ? ` (${edge.pct}%)` : ''),
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 16,
          height: 16,
          color,
        },
        type: 'smoothstep',
        animated: true,
        style: { strokeWidth: 2, stroke: color },
        labelStyle: {
          fontSize: 11,
          fontWeight: 600,
          fill: '#374151',
        },
        labelBgStyle: {
          fill: '#ffffff',
          fillOpacity: 0.9,
        },
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 4,
      };
    });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [expandingNodeId, setNodes, setEdges]);

  // Merge new data into store (avoiding duplicates)
  const mergeGraphData = useCallback((response: GraphResponse) => {
    let newNodesCount = 0;
    let newEdgesCount = 0;

    response.nodes.forEach((node) => {
      if (!nodeStore.current.has(node.id)) {
        nodeStore.current.set(node.id, node);
        newNodesCount++;
      }
    });

    response.edges.forEach((edge) => {
      if (!edgeStore.current.has(edge.id)) {
        edgeStore.current.set(edge.id, edge);
        newEdgesCount++;
      }
    });

    updateFlowFromStore();
    return { newNodesCount, newEdgesCount };
  }, [updateFlowFromStore]);

  // Handle search input with suggestions
  const handleSearchInput = async (value: string) => {
    setSearchQuery(value);

    if (value.length < 2) {
      setSearchResults([]);
      setShowSearchDropdown(false);
      return;
    }

    try {
      const response = await searchApi.suggest(value, 10);
      const suggestions = response.data;

      // Filter to only taxpayers
      const taxpayers = suggestions.filter((item: any) => item.entity_type === 'TAXPAYER');
      setSearchResults(taxpayers);
      setShowSearchDropdown(taxpayers.length > 0);
    } catch (err) {
      console.error('Search suggestion error:', err);
      setSearchResults([]);
      setShowSearchDropdown(false);
    }
  };

  // Select taxpayer from dropdown
  const handleSelectTaxpayer = (taxpayer: any) => {
    setNpwp(taxpayer.npwp_masked || taxpayer.id.toString());
    setSearchQuery(taxpayer.name);
    setShowSearchDropdown(false);
    setSearchResults([]);
  };

  // Initial search
  const handleSearch = async () => {
    if (!npwp.trim() && !searchQuery.trim()) {
      setError('Masukkan NPWP atau nama perusahaan untuk mencari');
      return;
    }

    setIsLoading(true);
    setError('');
    nodeStore.current.clear();
    edgeStore.current.clear();

    try {
      // First, search for taxpayer by NPWP or name
      const query = searchQuery.trim() || npwp.replace(/[.-]/g, '');
      const searchResponse = await searchApi.search({
        q: query,
        entity_type: 'TAXPAYER',
        page: 1,
        page_size: 1,
      });

      const results = searchResponse.data.items || searchResponse.data;
      if (!results || results.length === 0) {
        setError(`Tidak ditemukan wajib pajak dengan: ${query}`);
        setIsLoading(false);
        return;
      }

      const taxpayer = results[0];

      // Load network graph for the found taxpayer
      const graphResponse = await networkApi.graph({
        root_type: 'TAXPAYER',
        root_id: taxpayer.id,
        year,
        depth,
        max_nodes: maxNodes,
      });

      const data: GraphResponse = graphResponse.data;
      mergeGraphData(data);
      setTruncated(data.truncated);
    } catch (err: any) {
      console.error('Search error:', err);
      setError(err.response?.data?.detail || 'Gagal memuat data jaringan');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle double-click expansion
  const handleNodeExpand = useCallback(async (node: NetworkNode) => {
    if (expandingNodeId) return; // Prevent multiple expansions

    setExpandingNodeId(node.id);
    setError('');

    try {
      const response = await networkApi.expand({
        node_type: node.entity_type,
        node_id: node.entity_id,
        year,
        depth: 1,
        edge_types: selectedEdgeTypes,
        max_neighbors: 50,
      });

      const data: GraphResponse = response.data;

      // Adjust layers for new nodes (relative to expanded node)
      const adjustedNodes = data.nodes.map((n) => ({
        ...n,
        layer: n.layer === 0 ? node.layer : node.layer + n.layer,
      }));

      const { newNodesCount, newEdgesCount } = mergeGraphData({
        ...data,
        nodes: adjustedNodes,
      });

      if (newNodesCount === 0 && newEdgesCount === 0) {
        // Show toast that no new connections found
        console.log('No new connections found for this node');
      }
    } catch (err: any) {
      console.error('Expand error:', err);
      setError(err.response?.data?.detail || 'Gagal memperluas jaringan');
    } finally {
      setExpandingNodeId(null);
    }
  }, [expandingNodeId, year, selectedEdgeTypes, mergeGraphData]);

  // Handle node click
  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    const nodeData = nodeStore.current.get(node.id);
    setSelectedNode(nodeData || null);
  }, []);

  // Toggle edge type filter
  const toggleEdgeType = (type: string) => {
    setSelectedEdgeTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  // Toggle category visibility
  const toggleCategory = (category: string) => {
    setVisibleCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  // Count connections for selected node
  const connectionCount = useMemo(() => {
    if (!selectedNode) return 0;
    return Array.from(edgeStore.current.values()).filter(
      (e) => e.source === selectedNode.id || e.target === selectedNode.id
    ).length;
  }, [selectedNode, edges]);

  // Filter nodes by visible categories
  const filteredNodes = useMemo(() => {
    return nodes.filter((node) => {
      const category = node.data.category || node.data.entity_type;
      return visibleCategories.has(category);
    });
  }, [nodes, visibleCategories]);

  // Filter edges to only show connections between visible nodes
  const filteredEdges = useMemo(() => {
    const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter(
      (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
    );
  }, [filteredNodes, edges]);

  // Export PNG
  const handleExport = async () => {
    if (!canvasRef.current) return;
    try {
      await exportNetworkPng({
        element: canvasRef.current,
        filename: `jaringan_${npwp.replace(/[.-]/g, '')}_${year}.png`,
        scale: 2,
        includeLegend: false,
      });
    } catch (err) {
      console.error('Export error:', err);
    }
  };

  if (userLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-16 w-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full" />
      </div>
    );
  }

  if (!user) return null;

  const years = [2025, 2024, 2023, 2022, 2021, 2020];

  return (
    <MainLayout title="Jaringan Wajib Pajak">
      <div className="space-y-6" ref={viewRef}>
        {/* Search Controls */}
        <div className="glass-panel p-6">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div className="md:col-span-2 relative">
              <label className="block text-xs font-bold text-gray-600 mb-2">NPWP atau Nama Perusahaan</label>
              <input
                type="text"
                value={searchQuery || npwp}
                onChange={(e) => {
                  handleSearchInput(e.target.value);
                  if (!e.target.value.includes('.')) {
                    setNpwp('');
                  }
                }}
                onFocus={() => {
                  if (searchResults.length > 0) {
                    setShowSearchDropdown(true);
                  }
                }}
                onBlur={() => {
                  setTimeout(() => setShowSearchDropdown(false), 200);
                }}
                placeholder="Cari NPWP atau nama perusahaan..."
                className="input-field"
              />

              {/* Search Dropdown */}
              {showSearchDropdown && searchResults.length > 0 && (
                <div className="absolute z-50 w-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 max-h-64 overflow-y-auto">
                  {searchResults.map((result: any) => (
                    <button
                      key={result.id}
                      onClick={() => handleSelectTaxpayer(result)}
                      className="w-full px-4 py-3 text-left hover:bg-indigo-50 border-b border-gray-100 last:border-b-0 transition-colors"
                    >
                      <div className="font-medium text-gray-900 text-sm">{result.name}</div>
                      {result.npwp_masked && (
                        <div className="text-xs text-gray-500 font-mono mt-1">{result.npwp_masked}</div>
                      )}
                      {result.address && (
                        <div className="text-xs text-gray-400 mt-1 truncate">{result.address}</div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-2">Tahun Pajak</label>
              <select
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="input-field"
              >
                {years.map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-2">Depth</label>
              <select
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
                className="input-field"
              >
                {[1, 2, 3, 4, 5].map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-2">Max Nodes</label>
              <input
                type="number"
                min={50}
                max={1000}
                value={maxNodes}
                onChange={(e) => setMaxNodes(Number(e.target.value))}
                className="input-field"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={(!npwp.trim() && !searchQuery.trim()) || isLoading}
                className="w-full btn-primary disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                    <span>Mencari...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <span>Cari</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Edge Type Filters */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <label className="block text-xs font-bold text-gray-600 mb-2">Filter Tipe Relasi</label>
            <div className="flex flex-wrap gap-2">
              {edgeTypeOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => toggleEdgeType(opt.value)}
                  className={`
                    px-3 py-1.5 rounded-full text-xs font-semibold border-2 transition-all
                    ${selectedEdgeTypes.includes(opt.value)
                      ? 'text-white'
                      : 'bg-white text-gray-600 border-gray-200'
                    }
                  `}
                  style={{
                    backgroundColor: selectedEdgeTypes.includes(opt.value) ? opt.color : undefined,
                    borderColor: opt.color,
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Error/Warning Messages */}
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
              {error}
            </div>
          )}
          {truncated && (
            <div className="mt-4 bg-amber-50 border border-amber-200 text-amber-700 px-4 py-3 rounded-xl text-sm">
              ⚠️ Hasil dipotong karena melebihi batas node ({maxNodes}). Kurangi depth atau tingkatkan batas.
            </div>
          )}
        </div>

        {/* Graph Area */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
          {/* Main Graph */}
          <div className="glass-panel relative">
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-700">
                Nodes: {filteredNodes.length} | Edges: {filteredEdges.length}
              </span>
            </div>
            <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
              <button
                onClick={handleExport}
                className="btn-secondary text-sm px-3 py-1.5"
                disabled={filteredNodes.length === 0}
              >
                Export PNG
              </button>
            </div>

            <div ref={canvasRef} className="h-[600px] bg-gradient-to-br from-gray-50 to-white rounded-2xl">
              {filteredNodes.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center space-y-4 max-w-md px-4">
                    <div className="h-20 w-20 rounded-full bg-indigo-100 flex items-center justify-center mx-auto">
                      <svg className="w-10 h-10 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-bold text-gray-900">Jaringan Wajib Pajak</h3>
                    <p className="text-sm text-gray-600">
                      Masukkan <strong>NPWP</strong> dan klik <strong>Cari</strong> untuk melihat jaringan kepemilikan dan afiliasi.
                      Double-click pada node untuk memperluas jaringan secara dinamis.
                    </p>
                  </div>
                </div>
              ) : (
                <ReactFlow
                  nodes={filteredNodes}
                  edges={filteredEdges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onNodeClick={handleNodeClick}
                  onNodeDoubleClick={(_, node) => {
                    const nodeData = nodeStore.current.get(node.id);
                    if (nodeData) handleNodeExpand(nodeData);
                  }}
                  nodeTypes={{
                    networkNode: NetworkNodeCard,
                  }}
                  fitView
                  nodesDraggable
                  nodesConnectable={false}
                  elementsSelectable
                  minZoom={0.1}
                  maxZoom={2}
                >
                  <MiniMap
                    nodeColor={(node) => {
                      const category = node.data?.category || node.data?.entity_type;
                      const style = categoryStyles[category];
                      return style?.bg.includes('blue') ? '#3b82f6' :
                             style?.bg.includes('emerald') ? '#10b981' :
                             style?.bg.includes('amber') ? '#f59e0b' :
                             style?.bg.includes('purple') ? '#8b5cf6' : '#6b7280';
                    }}
                  />
                  <Controls />
                  <Background gap={20} />
                </ReactFlow>
              )}
            </div>

            {/* Node Detail Popover */}
            <NodeDetailPopover
              node={selectedNode}
              onClose={() => setSelectedNode(null)}
              connections={connectionCount}
            />
          </div>

          {/* Right Sidebar - Legend & Filters */}
          <div className="space-y-4">
            <CategoryLegend
              onCategoryToggle={toggleCategory}
              visibleCategories={visibleCategories}
            />

            {/* Instructions */}
            <div className="glass-panel p-4">
              <div className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">Cara Penggunaan</div>
              <ul className="text-xs text-gray-600 space-y-1">
                <li>• <strong>Klik</strong> node untuk melihat detail</li>
                <li>• <strong>Double-click</strong> untuk memperluas jaringan</li>
                <li>• <strong>Drag</strong> untuk menggeser node</li>
                <li>• <strong>Scroll</strong> untuk zoom in/out</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

export default function JaringanWPPage() {
  return (
    <ReactFlowProvider>
      <JaringanWPContent />
    </ReactFlowProvider>
  );
}
