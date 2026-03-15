'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  useReactFlow,
  Node,
  Edge,
  EdgeProps,
  NodeChange,
  EdgeChange,
  getSmoothStepPath,
  EdgeLabelRenderer,
  BaseEdge,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';

import MainLayout from '@/components/MainLayout';
import EntityAutocompleteInput, { EntitySuggestion } from '@/components/EntityAutocompleteInput';
import { graphIntelApi, networkApi } from '@/lib/api';
import { exportNetworkPng } from '@/lib/networkExport';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type NetworkNode = {
  id: string;
  entity_id: number;
  entity_type: string;
  entity_subtype?: string | null;
  name: string;
  npwp?: string | null;
  location_label: string;
  layer: number;
  category?: 'Entity' | 'Officer' | 'Address' | 'Intermediary';
  // injected by frontend for detector overlay
  detectorBadges?: string[];
};

type NetworkEdge = {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  label: string;
  layer: number;
  pct?: number | null;
  confidence?: number | null;
  notes?: string | null;
  source_ref?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
};

type DetectorResult = {
  detection_type: string;
  risk_level?: string;
  risk_score?: number;
  anomaly_score?: number;
  summary?: string;
  root_entity_id?: number;
  reason_codes?: string[];
  [key: string]: unknown;
};

// ---------------------------------------------------------------------------
// Colours and styles
// ---------------------------------------------------------------------------
const CATEGORY_STYLES: Record<string, { bg: string; border: string; icon: string }> = {
  Entity:       { bg: '#3b82f6', border: '#2563eb', icon: '🏢' },
  Officer:      { bg: '#10b981', border: '#059669', icon: '👤' },
  Address:      { bg: '#f59e0b', border: '#d97706', icon: '📍' },
  Intermediary: { bg: '#8b5cf6', border: '#7c3aed', icon: '🔗' },
};

const EDGE_COLORS: Record<string, string> = {
  OWNERSHIP:        '#3b82f6',
  CONTROL:          '#8b5cf6',
  FAMILY:           '#ec4899',
  AFFILIATION_OTHER:'#f59e0b',
};

const RISK_COLOURS: Record<string, string> = {
  LOW:       'bg-green-100 text-green-800',
  MEDIUM:    'bg-yellow-100 text-yellow-800',
  HIGH:      'bg-orange-100 text-orange-800',
  VERY_HIGH: 'bg-red-100 text-red-800',
};

const DETECTORS = [
  { id: 'ai-discovery',              label: 'AI Discovery',            icon: '🔍' },
  { id: 'ownership-pyramid',         label: 'Ownership Pyramid',       icon: '🔺' },
  { id: 'circular-detection',        label: 'Circular Transactions',   icon: '🔄' },
  { id: 'beneficial-owner-inference',label: 'BO Inference',            icon: '👁️' },
  { id: 'vat-carousel',              label: 'VAT Carousel',            icon: '🎠' },
  { id: 'shell-company',             label: 'Shell Company',           icon: '🐚' },
  { id: 'nominee-director',          label: 'Nominee Director',        icon: '🎭' },
  { id: 'trade-mispricing',          label: 'Trade Mispricing',        icon: '💱' },
];

// ---------------------------------------------------------------------------
// Custom node renderer
// ---------------------------------------------------------------------------
const HANDLE_STYLE: React.CSSProperties = {
  opacity: 0,
  width: 8,
  height: 8,
  minWidth: 8,
  border: 'none',
  background: 'transparent',
  pointerEvents: 'none',
};

function GraphNodeCard({ data }: { data: NetworkNode & { onClick: () => void; isHighlighted?: boolean; isDimmed?: boolean; isExpanded?: boolean } }) {
  const style = CATEGORY_STYLES[data.category || 'Entity'] || CATEGORY_STYLES.Entity;
  const hasBadges = data.detectorBadges && data.detectorBadges.length > 0;

  return (
    <>
      <Handle type="target" position={Position.Left} style={HANDLE_STYLE} />
      <Handle type="target" position={Position.Top} style={HANDLE_STYLE} />
      <div
        onClick={data.onClick}
        style={{
          background: style.bg,
          border: `2px solid ${data.isHighlighted ? '#facc15' : data.isExpanded ? '#a78bfa' : style.border}`,
          boxShadow: data.isHighlighted ? '0 0 0 3px #facc15' : data.isExpanded ? '0 0 0 2px #a78bfa' : undefined,
          borderRadius: 8,
          padding: '6px 10px',
          cursor: 'pointer',
          minWidth: 140,
          maxWidth: 200,
          color: '#000000',
          fontSize: 11,
          position: 'relative',
          opacity: data.isDimmed ? 0.2 : 1,
          filter: data.isDimmed ? 'grayscale(0.6) brightness(0.9)' : undefined,
          transition: 'opacity 0.2s, filter 0.2s',
        }}
    >
      {/* Detector alert badge */}
      {hasBadges && (
        <div style={{
          position: 'absolute',
          top: -8,
          right: -8,
          background: '#ef4444',
          borderRadius: '50%',
          width: 16,
          height: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 9,
          fontWeight: 700,
          border: '1.5px solid white',
        }}>
          {data.detectorBadges!.length}
        </div>
      )}

      <div style={{ fontWeight: 700, marginBottom: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {style.icon} {data.name.slice(0, 24)}{data.name.length > 24 ? '…' : ''}
      </div>

      {/* NPWP — shown only for taxpayer/entity nodes when available */}
      {data.npwp && (
        <div style={{ fontSize: 9, fontFamily: 'monospace', opacity: 0.85, marginBottom: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {data.npwp}
        </div>
      )}

      <div style={{ opacity: 0.8, fontSize: 9, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {data.entity_subtype || data.entity_type}
      </div>

      <div style={{ fontSize: 9, opacity: 0.65, marginTop: 1 }}>
        L{data.layer}
      </div>

      {/* Detector reason codes as micro tags */}
      {hasBadges && (
        <div style={{ marginTop: 3, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
          {data.detectorBadges!.slice(0, 2).map(code => (
            <span key={code} style={{
              background: 'rgba(239,68,68,0.3)',
              border: '1px solid rgba(239,68,68,0.6)',
              borderRadius: 3,
              padding: '0 3px',
              fontSize: 8,
              lineHeight: '12px',
            }}>
              {code}
            </span>
          ))}
          {data.detectorBadges!.length > 2 && (
            <span style={{ fontSize: 8, opacity: 0.7 }}>+{data.detectorBadges!.length - 2}</span>
          )}
        </div>
      )}
      </div>
      <Handle type="source" position={Position.Right} style={HANDLE_STYLE} />
      <Handle type="source" position={Position.Bottom} style={HANDLE_STYLE} />
    </>
  );
}

const nodeTypes = { graphNode: GraphNodeCard };

// ---------------------------------------------------------------------------
// Custom edge renderer with hover tooltip
// ---------------------------------------------------------------------------
function GraphEdge({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  data, markerEnd, selected,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, borderRadius: 12 });
  const [hovered, setHovered] = useState(false);
  const edgeData = data as NetworkEdge;
  const color = EDGE_COLORS[edgeData?.relationship_type] || '#94a3b8';

  // Full readable label: "OWNERSHIP" → "OWNERSHIP", "AFFILIATION_OTHER" → "AFFIL. OTHER"
  const fullLabel = edgeData?.relationship_type
    ? edgeData.relationship_type.replace(/_/g, '\u00a0') // non-breaking space
    : '';

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{ stroke: selected ? '#f59e0b' : '#374151', strokeWidth: selected ? 3 : 2 }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            fontSize: 10,
            fontWeight: 700,
            background: 'rgba(255,255,255,0.95)',
            color: '#111827',
            padding: '2px 6px',
            borderRadius: 4,
            border: `1.5px solid ${color}`,
            cursor: 'pointer',
            pointerEvents: 'all',
            userSelect: 'none',
            zIndex: 1000,
            whiteSpace: 'nowrap',
            letterSpacing: '0.02em',
            boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
          }}
          className="nodrag nopan"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          {fullLabel}
          {edgeData?.pct != null && ` ${edgeData.pct.toFixed(0)}%`}

          {/* Hover tooltip */}
          {hovered && (
            <div style={{
              position: 'absolute',
              bottom: '110%',
              left: '50%',
              transform: 'translateX(-50%)',
              background: '#ffffff',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              padding: '6px 8px',
              minWidth: 160,
              maxWidth: 240,
              zIndex: 2000,
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            }}>
              <div style={{ fontWeight: 700, color: '#111827', marginBottom: 3 }}>
                {edgeData?.relationship_type}
              </div>
              {edgeData?.pct != null && (
                <div style={{ color: '#374151', fontSize: 9 }}>
                  Kepemilikan: <span style={{ color: '#2563eb', fontWeight: 600 }}>{edgeData.pct.toFixed(2)}%</span>
                </div>
              )}
              {edgeData?.confidence != null && (
                <div style={{ color: '#374151', fontSize: 9 }}>
                  Confidence: <span style={{ color: '#059669', fontWeight: 600 }}>{(edgeData.confidence * 100).toFixed(0)}%</span>
                </div>
              )}
              {edgeData?.notes && (
                <div style={{ color: '#4b5563', fontSize: 9, marginTop: 3, fontStyle: 'italic' }}>
                  {edgeData.notes}
                </div>
              )}
              {edgeData?.effective_from && (
                <div style={{ color: '#6b7280', fontSize: 8, marginTop: 2 }}>
                  {edgeData.effective_from}{edgeData.effective_to ? ` → ${edgeData.effective_to}` : ' → sekarang'}
                </div>
              )}
            </div>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const edgeTypes = { graphEdge: GraphEdge };

// ---------------------------------------------------------------------------
// Tree-aware layered layout
// ---------------------------------------------------------------------------
function layoutNodes(rawNodes: NetworkNode[], rawEdges: NetworkEdge[]): Node[] {
  if (rawNodes.length === 0) return [];

  const X_STEP = 380;   // horizontal px between layers
  const NODE_H = 80;
  const Y_GAP = 32;     // vertical gap between sibling nodes
  const UNIT = NODE_H + Y_GAP;

  // Build parent→children from edges (only cross-layer edges)
  const nodeById = new Map(rawNodes.map(n => [n.id, n]));
  const children = new Map<string, string[]>();
  const parentOf = new Map<string, string>();

  rawEdges.forEach(e => {
    const src = nodeById.get(e.source);
    const tgt = nodeById.get(e.target);
    if (!src || !tgt || src.layer === tgt.layer) return;
    const [par, chi] = src.layer < tgt.layer ? [src, tgt] : [tgt, src];
    if (!parentOf.has(chi.id)) {
      parentOf.set(chi.id, par.id);
      children.set(par.id, [...(children.get(par.id) ?? []), chi.id]);
    }
  });

  const posMap = new Map<string, { x: number; y: number }>();
  const visited = new Set<string>();

  // Recursive subtree placement: returns height consumed
  function place(id: string, layer: number, topY: number): number {
    if (visited.has(id)) {
      // cycle guard – place at current topY
      if (!posMap.has(id)) posMap.set(id, { x: layer * X_STEP, y: topY + UNIT / 2 });
      return UNIT;
    }
    visited.add(id);

    const kids = children.get(id) ?? [];
    if (kids.length === 0) {
      posMap.set(id, { x: layer * X_STEP, y: topY + UNIT / 2 });
      return UNIT;
    }

    let cy = topY;
    for (const kid of kids) {
      cy += place(kid, layer + 1, cy);
    }

    // center parent on its children
    const fy = posMap.get(kids[0])!.y;
    const ly = posMap.get(kids[kids.length - 1])!.y;
    posMap.set(id, { x: layer * X_STEP, y: (fy + ly) / 2 });
    return cy - topY;
  }

  // Place roots (layer 0), then any roots at deeper layers with no parent
  const roots = rawNodes.filter(n => n.layer === 0 || (!parentOf.has(n.id) && n.layer === Math.min(...rawNodes.map(r => r.layer))));
  let rootY = 0;
  for (const root of roots) {
    rootY += place(root.id, root.layer, rootY);
  }

  // Place remaining nodes not yet positioned (isolated / cross-layer-only nodes)
  rawNodes.forEach(n => {
    if (!posMap.has(n.id)) {
      posMap.set(n.id, { x: n.layer * X_STEP, y: rootY });
      rootY += UNIT;
    }
  });

  return rawNodes.map(n => ({
    id: n.id,
    type: 'graphNode',
    position: posMap.get(n.id)!,
    data: { ...n },
  }));
}

function buildFlowEdges(rawEdges: NetworkEdge[]): Edge[] {
  return rawEdges.map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'graphEdge',
    data: e,
    markerEnd: { type: MarkerType.ArrowClosed, color: '#374151', width: 22, height: 22 },
    style: { stroke: '#374151' },
  }));
}

// ---------------------------------------------------------------------------
// Inner canvas component — must live inside ReactFlowProvider to use useReactFlow
// ---------------------------------------------------------------------------
type GraphCanvasProps = {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (c: NodeChange[]) => void;
  onEdgesChange: (c: EdgeChange[]) => void;
  onEdgeClick: (evt: React.MouseEvent, edge: Edge) => void;
  onNodeDoubleClick: (evt: React.MouseEvent, node: Node) => void;
  onPaneClick: () => void;
  fitViewToken: number;
};

function GraphCanvas({
  nodes, edges,
  onNodesChange, onEdgesChange,
  onEdgeClick, onNodeDoubleClick, onPaneClick,
  fitViewToken,
}: GraphCanvasProps) {
  const { fitView } = useReactFlow();
  const prevToken = useRef(0);

  useEffect(() => {
    if (fitViewToken === prevToken.current) return;
    prevToken.current = fitViewToken;
    // Small delay ensures ReactFlow has finished positioning nodes before fitting
    const t = setTimeout(() => {
      fitView({ duration: 450, padding: 0.18, maxZoom: 1.4 });
    }, 80);
    return () => clearTimeout(t);
  }, [fitViewToken, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onEdgeClick={onEdgeClick}
      onNodeDoubleClick={onNodeDoubleClick}
      onPaneClick={onPaneClick}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      minZoom={0.04}
      maxZoom={3}
      style={{ background: '#ffffff' }}
    >
      <Background color="#d1d5db" gap={20} />
      <Controls style={{ background: '#f9fafb', border: '1px solid #d1d5db', borderRadius: 8 }} />
    </ReactFlow>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function NetworkExplorerPage() {
  const searchParams = useSearchParams();

  const [npwp, setNpwp] = useState(() => searchParams.get('npwp') || '');
  const [year, setYear] = useState(() => searchParams.get('year') || String(new Date().getFullYear() - 1));
  const [npwp2, setNpwp2] = useState('');
  const [depth, setDepth] = useState('2');
  const [maxNodes, setMaxNodes] = useState('300');

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graphMeta, setGraphMeta] = useState<{
    mode: string; truncated: boolean; root_entity_id?: number;
    path_analysis?: Record<string, unknown>;
  } | null>(null);

  // Raw graph data store for edge lookup
  const rawEdgesRef = useRef<NetworkEdge[]>([]);

  // Expand/collapse state
  const [expandedSet, setExpandedSet] = useState<Set<string>>(new Set());
  const expandedChildrenRef = useRef<Map<string, { nodeIds: Set<string>; edgeIds: Set<string> }>>(new Map());
  const originalNodesRef = useRef<Map<string, NetworkNode>>(new Map());
  const originalEdgesRef = useRef<Map<string, NetworkEdge>>(new Map());
  const allRawNodesMapRef = useRef<Map<string, NetworkNode>>(new Map());
  const allRawEdgesMapRef = useRef<Map<string, NetworkEdge>>(new Map());

  // Focus/highlight state for suspect double-click
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [suspectStatus, setSuspectStatus] = useState<{ name: string; found: boolean } | null>(null);

  // Selected node/edge detail
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<NetworkEdge | null>(null);

  // Detector panel state
  const [activeDetector, setActiveDetector] = useState<string | null>(null);
  const [detectorLoading, setDetectorLoading] = useState(false);
  const [detectorResult, setDetectorResult] = useState<DetectorResult | null>(null);
  const [detectorError, setDetectorError] = useState<string | null>(null);

  // Category visibility filter
  const [visibleCategories, setVisibleCategories] = useState<Set<string>>(
    new Set(['Entity', 'Officer', 'Address', 'Intermediary'])
  );

  const graphRef = useRef<HTMLDivElement>(null);
  const [fitViewToken, setFitViewToken] = useState(0);

  const handleEntity1Select = (entity: EntitySuggestion) => {
    if (entity.npwp_masked) setNpwp(entity.npwp_masked);
  };
  const handleEntity2Select = (entity: EntitySuggestion) => {
    if (entity.npwp_masked) setNpwp2(entity.npwp_masked);
  };

  // Build ReactFlow nodes with detector badges injected
  const buildNodesWithHandlers = useCallback((
    rawNodes: NetworkNode[],
    result: DetectorResult | null,
    rawEdges: NetworkEdge[],
  ): Node[] => {
    const highlightId = result?.root_entity_id
      ? `TAXPAYER:${result.root_entity_id}`
      : null;
    const reasonCodes: string[] = Array.isArray(result?.reason_codes) ? result!.reason_codes as string[] : [];

    const positioned = layoutNodes(rawNodes, rawEdges);
    return positioned.map(n => ({
      ...n,
      data: {
        ...n.data,
        detectorBadges: n.id === highlightId && reasonCodes.length ? reasonCodes : undefined,
        isHighlighted: n.id === highlightId && reasonCodes.length > 0,
        onClick: () => setSelectedNode(n.data as NetworkNode),
      },
    }));
  }, []);

  // ---------------------------------------------------------------------------
  // Graph search
  // ---------------------------------------------------------------------------
  const handleSearch = useCallback(async () => {
    if (!npwp || !year) return;
    setLoading(true);
    setError(null);
    setGraphMeta(null);
    setSelectedNode(null);
    setSelectedEdge(null);
    setDetectorResult(null);
    setExpandedSet(new Set());
    setFocusedNodeId(null);
    expandedChildrenRef.current.clear();

    try {
      const res = await graphIntelApi.search({
        npwp,
        year: Number(year),
        npwp2: npwp2 || undefined,
        depth: Number(depth),
        max_nodes: Number(maxNodes),
      });
      const data = res.data;
      const rawNodes: NetworkNode[] = data.graph?.nodes || [];
      const rawEdges: NetworkEdge[] = data.graph?.edges || [];

      // Populate tracking refs
      const nodeMap = new Map<string, NetworkNode>();
      rawNodes.forEach(n => nodeMap.set(n.id, n));
      const edgeMap = new Map<string, NetworkEdge>();
      rawEdges.forEach(e => edgeMap.set(e.id, e));
      originalNodesRef.current = new Map(nodeMap);
      originalEdgesRef.current = new Map(edgeMap);
      allRawNodesMapRef.current = nodeMap;
      allRawEdgesMapRef.current = edgeMap;
      rawEdgesRef.current = rawEdges;

      const positioned = buildNodesWithHandlers(rawNodes, null, rawEdges);
      setNodes(positioned);
      setEdges(buildFlowEdges(rawEdges));
      setGraphMeta({
        mode: data.mode,
        truncated: data.truncated,
        root_entity_id: data.root_entity_id,
        path_analysis: data.path_analysis,
      });
      // Sync search input to the root entity's NPWP so autocomplete stays consistent
      const rootNode = rawNodes.find(n => n.layer === 0);
      if (rootNode?.npwp) setNpwp(rootNode.npwp);
      setFitViewToken(t => t + 1);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Search failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [npwp, year, npwp2, depth, maxNodes, setNodes, setEdges, buildNodesWithHandlers]);

  // Auto-load on mount when URL has NPWP
  useEffect(() => {
    const urlNpwp = searchParams.get('npwp');
    if (urlNpwp && urlNpwp.length > 4) handleSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-inject detector badges when detector result changes
  useEffect(() => {
    if (nodes.length === 0) return;
    setNodes(prev => prev.map(n => {
      const raw = n.data as NetworkNode;
      const highlightId = detectorResult?.root_entity_id ? `TAXPAYER:${detectorResult.root_entity_id}` : null;
      const reasonCodes: string[] = Array.isArray(detectorResult?.reason_codes) ? detectorResult!.reason_codes as string[] : [];
      const isHighlighted = n.id === highlightId && reasonCodes.length > 0;
      return {
        ...n,
        data: {
          ...n.data,
          detectorBadges: isHighlighted ? reasonCodes : undefined,
          isHighlighted,
          onClick: () => setSelectedNode(raw),
        },
      };
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detectorResult]);

  // ---------------------------------------------------------------------------
  // Detector handler
  // ---------------------------------------------------------------------------
  const runDetector = useCallback(async (detectorId: string) => {
    if (!npwp || !year) {
      setDetectorError('Please search for a taxpayer first.');
      return;
    }
    setActiveDetector(detectorId);
    setDetectorLoading(true);
    setDetectorResult(null);
    setDetectorError(null);
    setSelectedEdge(null);

    try {
      let res;
      const body = { npwp, year: Number(year), max_depth: Number(depth) };
      switch (detectorId) {
        case 'ai-discovery':              res = await graphIntelApi.aiDiscovery(body); break;
        case 'ownership-pyramid':         res = await graphIntelApi.ownershipPyramid(body); break;
        case 'circular-detection':        res = await graphIntelApi.circularDetection(body); break;
        case 'beneficial-owner-inference':res = await graphIntelApi.beneficialOwnerInference(body); break;
        case 'vat-carousel':              res = await graphIntelApi.vatCarousel(body); break;
        case 'shell-company':             res = await graphIntelApi.shellCompany(body); break;
        case 'nominee-director':          res = await graphIntelApi.nomineeDirector({ year: Number(year) }); break;
        case 'trade-mispricing':          res = await graphIntelApi.tradeMispricing({ npwp, year: Number(year) }); break;
        default: throw new Error('Unknown detector');
      }
      setDetectorResult(res.data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Detector failed';
      setDetectorError(msg);
    } finally {
      setDetectorLoading(false);
    }
  }, [npwp, year, depth]);

  // ---------------------------------------------------------------------------
  // Edge click handler
  // ---------------------------------------------------------------------------
  const handleEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    const raw = rawEdgesRef.current.find(e => e.id === edge.id) || null;
    setSelectedEdge(raw);
    setSelectedNode(null);
  }, []);

  // ---------------------------------------------------------------------------
  // Double-click: expand / collapse node
  // ---------------------------------------------------------------------------
  const handleNodeDoubleClick = useCallback(async (_evt: React.MouseEvent, node: Node) => {
    const nodeId = node.id;
    const parts = nodeId.split(':');
    if (parts.length < 2) return;
    const nodeType = parts[0];
    const entityId = parseInt(parts[1]);

    if (expandedSet.has(nodeId)) {
      // ── Collapse ──────────────────────────────────────────────────────────
      const children = expandedChildrenRef.current.get(nodeId);
      if (!children) return;

      // Nodes/edges exclusively owned by this expansion (not original, not other expansions)
      const otherNodeIds = new Set<string>();
      const otherEdgeIds = new Set<string>();
      expandedChildrenRef.current.forEach((c, k) => {
        if (k !== nodeId) {
          c.nodeIds.forEach(id => otherNodeIds.add(id));
          c.edgeIds.forEach(id => otherEdgeIds.add(id));
        }
      });

      children.nodeIds.forEach(id => {
        if (!originalNodesRef.current.has(id) && !otherNodeIds.has(id)) {
          allRawNodesMapRef.current.delete(id);
        }
      });
      children.edgeIds.forEach(id => {
        if (!originalEdgesRef.current.has(id) && !otherEdgeIds.has(id)) {
          allRawEdgesMapRef.current.delete(id);
        }
      });

      expandedChildrenRef.current.delete(nodeId);
      const newExpanded = new Set(expandedSet);
      newExpanded.delete(nodeId);
      setExpandedSet(newExpanded);

      const allNodes = Array.from(allRawNodesMapRef.current.values());
      const allEdges = Array.from(allRawEdgesMapRef.current.values());
      rawEdgesRef.current = allEdges;
      setNodes(buildNodesWithHandlers(allNodes, detectorResult, allEdges));
      setEdges(buildFlowEdges(allEdges));
      setFitViewToken(t => t + 1);
    } else {
      // ── Expand ────────────────────────────────────────────────────────────
      try {
        const res = await networkApi.expand({
          node_type: nodeType,
          node_id: entityId,
          year: Number(year),
          depth: 1,
          max_neighbors: 50,
        });
        const newNodes: NetworkNode[] = res.data.nodes || [];
        const newEdges: NetworkEdge[] = res.data.edges || [];

        const addedNodeIds = new Set<string>();
        const addedEdgeIds = new Set<string>();
        newNodes.forEach(n => {
          if (!allRawNodesMapRef.current.has(n.id)) {
            allRawNodesMapRef.current.set(n.id, n);
            addedNodeIds.add(n.id);
          }
        });
        newEdges.forEach(e => {
          if (!allRawEdgesMapRef.current.has(e.id)) {
            allRawEdgesMapRef.current.set(e.id, e);
            addedEdgeIds.add(e.id);
          }
        });

        expandedChildrenRef.current.set(nodeId, { nodeIds: addedNodeIds, edgeIds: addedEdgeIds });
        const newExpanded = new Set(expandedSet);
        newExpanded.add(nodeId);
        setExpandedSet(newExpanded);

        const allNodes = Array.from(allRawNodesMapRef.current.values());
        const allEdges = Array.from(allRawEdgesMapRef.current.values());
        rawEdgesRef.current = allEdges;
        setNodes(buildNodesWithHandlers(allNodes, detectorResult, allEdges));
        setEdges(buildFlowEdges(allEdges));
        setFitViewToken(t => t + 1);
      } catch {
        // silently ignore expand errors
      }
    }
  }, [expandedSet, year, detectorResult, buildNodesWithHandlers, setNodes, setEdges]);

  // ---------------------------------------------------------------------------
  // Filter by category + focus dimming
  // ---------------------------------------------------------------------------
  const filteredNodes = useMemo(() => {
    const connectedIds: Set<string> | null = focusedNodeId
      ? (() => {
          const ids = new Set<string>([focusedNodeId]);
          rawEdgesRef.current.forEach(e => {
            if (e.source === focusedNodeId) ids.add(e.target);
            if (e.target === focusedNodeId) ids.add(e.source);
          });
          return ids;
        })()
      : null;

    return nodes.map(n => ({
      ...n,
      hidden: !visibleCategories.has((n.data as NetworkNode).category || 'Entity'),
      data: {
        ...n.data,
        isDimmed: connectedIds !== null && !connectedIds.has(n.id),
        isExpanded: expandedSet.has(n.id),
      },
    }));
  }, [nodes, visibleCategories, focusedNodeId, expandedSet]);

  const toggleCategory = (cat: string) => {
    setVisibleCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat); else next.add(cat);
      return next;
    });
  };

  // ---------------------------------------------------------------------------
  // PNG export
  // ---------------------------------------------------------------------------
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = useCallback(async () => {
    const target = graphRef.current?.querySelector('.react-flow__renderer') as HTMLElement | null
      || graphRef.current;
    if (!target) return;
    setExportLoading(true);
    setExportError(null);
    try {
      await graphIntelApi.exportMetadata({ npwp, year: Number(year), depth: Number(depth) });
    } catch {/* non-critical */}
    try {
      // html-to-image first call often fails due to font/SVG init — retry once
      try {
        await exportNetworkPng({ element: target, filename: `graph-${npwp}-${year}.png`, scale: 2, backgroundColor: '#ffffff' });
      } catch {
        await new Promise(r => setTimeout(r, 300));
        await exportNetworkPng({ element: target, filename: `graph-${npwp}-${year}.png`, scale: 2, backgroundColor: '#ffffff' });
      }
    } catch (err: unknown) {
      setExportError('Gagal ekspor PNG. Coba lagi.');
      console.error('Export PNG failed:', err);
    } finally {
      setExportLoading(false);
    }
  }, [npwp, year, depth]);

  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 10 }, (_, i) => currentYear - i);

  // Right panel: what to show (edge detail takes priority over node, then detector)
  const rightPanelMode: 'node' | 'edge' | 'detector' | 'empty' =
    selectedEdge ? 'edge' :
    selectedNode ? 'node' :
    activeDetector ? 'detector' : 'empty';

  return (
    <MainLayout>
      <div className="flex h-screen overflow-hidden bg-gray-950">

        {/* ------------------------------------------------------------------ */}
        {/* LEFT PANEL                                                           */}
        {/* ------------------------------------------------------------------ */}
        <aside className="w-80 flex flex-col bg-gray-900 border-r border-gray-700 overflow-y-auto shrink-0">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🕸️</span> Graph Intelligence
            </h2>
            <p className="text-xs text-gray-400 mt-1">Network Explorer v2.0</p>
          </div>

          {/* Search Panel */}
          <div className="p-4 border-b border-gray-700 space-y-3">
            <h3 className="text-sm font-semibold text-gray-300">Search</h3>

            <EntityAutocompleteInput
              label="NPWP atau Nama *"
              value={npwp}
              onChange={setNpwp}
              onSelect={handleEntity1Select}
              placeholder="Cari NPWP atau nama WP…"
              required
              entityTypes={['TAXPAYER']}
            />

            <div>
              <label className="block text-xs text-gray-400 mb-1">Tahun *</label>
              <select
                value={year}
                onChange={e => setYear(e.target.value)}
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-600 focus:outline-none focus:border-blue-500"
              >
                {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>

            <EntityAutocompleteInput
              label="NPWP 2 (opsional – analisis jalur)"
              value={npwp2}
              onChange={setNpwp2}
              onSelect={handleEntity2Select}
              placeholder="Entitas kedua untuk path analysis…"
              entityTypes={['TAXPAYER']}
            />

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Depth (1–5)</label>
                <input
                  type="number" min={1} max={5} value={depth}
                  onChange={e => setDepth(e.target.value)}
                  className="w-full bg-gray-800 text-white text-sm rounded px-2 py-2 border border-gray-600 focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Max nodes</label>
                <input
                  type="number" min={50} max={1500} step={50} value={maxNodes}
                  onChange={e => setMaxNodes(e.target.value)}
                  className="w-full bg-gray-800 text-white text-sm rounded px-2 py-2 border border-gray-600 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <button
              onClick={handleSearch}
              disabled={loading || !npwp || !year}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-semibold py-2 rounded transition-colors"
            >
              {loading ? '⏳ Loading…' : '🔍 Search Graph'}
            </button>

            {error && (
              <div className="bg-red-900/50 border border-red-700 text-red-300 text-xs rounded p-2">
                {error}
              </div>
            )}
          </div>

          {/* Category Filters */}
          <div className="p-4 border-b border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Filters</h3>
            <div className="space-y-1">
              {Object.entries(CATEGORY_STYLES).map(([cat, style]) => (
                <button
                  key={cat}
                  onClick={() => toggleCategory(cat)}
                  className={`w-full flex items-center gap-2 px-3 py-1.5 rounded text-xs transition-colors ${
                    visibleCategories.has(cat) ? 'text-white font-medium' : 'text-gray-500 bg-gray-800'
                  }`}
                  style={visibleCategories.has(cat) ? { background: style.bg } : {}}
                >
                  <span>{style.icon}</span>
                  <span>{cat}</span>
                  {!visibleCategories.has(cat) && <span className="ml-auto opacity-50">hidden</span>}
                </button>
              ))}
            </div>
          </div>

          {/* Graph meta */}
          {graphMeta && (
            <div className="p-4 border-b border-gray-700 text-xs text-gray-400 space-y-1">
              <div><span className="text-gray-500">Mode:</span> <span className="text-white capitalize">{graphMeta.mode}</span></div>
              <div><span className="text-gray-500">Nodes:</span> <span className="text-white">{nodes.length}</span></div>
              <div><span className="text-gray-500">Edges:</span> <span className="text-white">{edges.length}</span></div>
              {graphMeta.truncated && (
                <div className="text-yellow-400">⚠ Graph truncated – increase max_nodes</div>
              )}
            </div>
          )}

          {/* Export */}
          {nodes.length > 0 && (
            <div className="p-4 border-b border-gray-700">
              <button
                onClick={handleExport}
                disabled={exportLoading}
                className="w-full bg-emerald-700 hover:bg-emerald-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm py-2 rounded transition-colors"
              >
                {exportLoading ? '⏳ Exporting…' : '📸 Export PNG'}
              </button>
              {exportError && (
                <p className="text-red-400 text-xs mt-1">{exportError}</p>
              )}
            </div>
          )}

          {/* Graph Intelligence Detectors */}
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Graph Intelligence</h3>
            <div className="space-y-1">
              {DETECTORS.map(d => (
                <button
                  key={d.id}
                  onClick={() => runDetector(d.id)}
                  disabled={detectorLoading}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded text-xs transition-colors ${
                    activeDetector === d.id
                      ? 'bg-purple-700 text-white'
                      : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  } disabled:opacity-50`}
                >
                  <span>{d.icon}</span>
                  <span>{d.label}</span>
                  {activeDetector === d.id && detectorLoading && (
                    <span className="ml-auto animate-spin">⏳</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* ------------------------------------------------------------------ */}
        {/* MAIN CANVAS                                                          */}
        {/* ------------------------------------------------------------------ */}
        <main className="flex-1 relative overflow-hidden">
          <div ref={graphRef} className="w-full h-full">
            <ReactFlowProvider>
              <GraphCanvas
                nodes={filteredNodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onEdgeClick={handleEdgeClick}
                onNodeDoubleClick={handleNodeDoubleClick}
                onPaneClick={() => { setFocusedNodeId(null); setSuspectStatus(null); }}
                fitViewToken={fitViewToken}
              />
            </ReactFlowProvider>

            {/* Empty state */}
            {nodes.length === 0 && !loading && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-center text-gray-400">
                  <div className="text-6xl mb-4">🕸️</div>
                  <div className="text-xl font-semibold text-gray-500">Graph Intelligence Explorer</div>
                  <div className="text-sm mt-2 text-gray-400">Enter NPWP and Year, then click Search Graph</div>
                </div>
              </div>
            )}

            {loading && (
              <div className="absolute inset-0 bg-gray-950/70 flex items-center justify-center">
                <div className="text-center text-white">
                  <div className="text-4xl animate-spin mb-3">⚙️</div>
                  <div>Loading graph…</div>
                </div>
              </div>
            )}
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 bg-white/95 border border-gray-200 rounded-lg p-3 text-xs pointer-events-none shadow-sm">
            <div className="text-gray-700 font-semibold mb-2">Legend</div>
            {Object.entries(CATEGORY_STYLES).map(([cat, style]) => (
              <div key={cat} className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded" style={{ background: style.bg }} />
                <span className="text-gray-700">{style.icon} {cat}</span>
              </div>
            ))}
            <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 rounded bg-gray-700" />
                <span className="text-gray-600 text-xs">Relationship →</span>
              </div>
              <div className="text-gray-400 text-xs">Hover edge label for detail</div>
            </div>
          </div>

          {/* Edge selection hint */}
          {nodes.length > 0 && !selectedEdge && !selectedNode && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-white/90 border border-gray-200 text-gray-600 text-xs px-3 py-1.5 rounded-full pointer-events-none shadow-sm">
              Click node/edge for details · Double-click node to expand/collapse
            </div>
          )}
        </main>

        {/* ------------------------------------------------------------------ */}
        {/* RIGHT PANEL: Node / Edge / Detector Results                         */}
        {/* ------------------------------------------------------------------ */}
        <aside className="w-80 flex flex-col bg-gray-900 border-l border-gray-700 overflow-y-auto shrink-0">

          {/* Node Detail */}
          {rightPanelMode === 'node' && selectedNode && (
            <div className="p-4 border-b border-gray-700">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-300">Node Detail</h3>
                <button onClick={() => setSelectedNode(null)} className="text-gray-500 hover:text-gray-300 text-xs">✕ Close</button>
              </div>
              <div className="bg-gray-800 rounded p-3 space-y-1.5 text-xs">
                <div className="text-white font-semibold text-sm">{selectedNode.name}</div>
                {selectedNode.npwp && (
                  <div className="font-mono text-blue-300 text-xs">{selectedNode.npwp}</div>
                )}
                <div><span className="text-gray-400">Type:</span> <span className="text-blue-400">{selectedNode.entity_type}</span></div>
                {selectedNode.entity_subtype && (
                  <div><span className="text-gray-400">Subtype:</span> <span className="text-gray-300">{selectedNode.entity_subtype}</span></div>
                )}
                <div><span className="text-gray-400">Category:</span> <span className="text-gray-300">{selectedNode.category}</span></div>
                <div><span className="text-gray-400">Location:</span> <span className="text-gray-300">{selectedNode.location_label}</span></div>
                <div><span className="text-gray-400">Layer:</span> <span className="text-gray-300">{selectedNode.layer}</span></div>
                <div><span className="text-gray-400">ID:</span> <span className="text-gray-500 font-mono">{selectedNode.id}</span></div>
                {selectedNode.detectorBadges && selectedNode.detectorBadges.length > 0 && (
                  <div className="pt-2 border-t border-gray-700">
                    <div className="text-red-400 font-medium mb-1">⚠ Detected Issues</div>
                    <div className="flex flex-wrap gap-1">
                      {selectedNode.detectorBadges.map(code => (
                        <span key={code} className="bg-red-900/40 text-red-300 px-2 py-0.5 rounded text-xs">
                          {code}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Edge Detail */}
          {rightPanelMode === 'edge' && selectedEdge && (
            <div className="p-4 border-b border-gray-700">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-300">Relationship Detail</h3>
                <button onClick={() => setSelectedEdge(null)} className="text-gray-500 hover:text-gray-300 text-xs">✕ Close</button>
              </div>
              <div className="bg-gray-800 rounded p-3 space-y-2 text-xs">
                {/* Type badge */}
                <div className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold text-white"
                  style={{ background: EDGE_COLORS[selectedEdge.relationship_type] || '#6b7280' }}>
                  {selectedEdge.relationship_type}
                </div>

                {selectedEdge.pct != null && (
                  <div><span className="text-gray-400">Kepemilikan:</span>
                    <span className="text-blue-300 font-bold ml-1">{selectedEdge.pct.toFixed(2)}%</span>
                  </div>
                )}
                {selectedEdge.confidence != null && (
                  <div><span className="text-gray-400">Confidence:</span>
                    <span className="text-emerald-300 font-bold ml-1">{(selectedEdge.confidence * 100).toFixed(0)}%</span>
                  </div>
                )}
                {selectedEdge.notes && (
                  <div>
                    <div className="text-gray-400 mb-1">Notes:</div>
                    <div className="text-gray-300 italic">{selectedEdge.notes}</div>
                  </div>
                )}
                {selectedEdge.source_ref && (
                  <div><span className="text-gray-400">Source:</span> <span className="text-gray-400">{selectedEdge.source_ref}</span></div>
                )}
                {(selectedEdge.effective_from || selectedEdge.effective_to) && (
                  <div>
                    <span className="text-gray-400">Period:</span>
                    <span className="text-gray-300 ml-1">
                      {selectedEdge.effective_from || '?'} → {selectedEdge.effective_to || 'sekarang'}
                    </span>
                  </div>
                )}
                <div className="pt-2 border-t border-gray-700 font-mono text-gray-600 text-xs">
                  <div>From: {selectedEdge.source}</div>
                  <div>To: {selectedEdge.target}</div>
                </div>
              </div>
            </div>
          )}

          {/* Empty node/edge hint */}
          {rightPanelMode === 'detector' || rightPanelMode === 'empty' ? (
            <div className="p-4 border-b border-gray-700">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Node / Edge Detail</h3>
              <p className="text-gray-500 text-xs">Click a node or edge label for details.</p>
            </div>
          ) : null}

          {/* Path Analysis */}
          {graphMeta?.path_analysis && (
            <div className="p-4 border-b border-gray-700">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Path Analysis</h3>
              <PathAnalysisPanel data={graphMeta.path_analysis} />
            </div>
          )}

          {/* Detector Results */}
          <div className="p-4 flex-1">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">
              {activeDetector
                ? DETECTORS.find(d => d.id === activeDetector)?.label || 'Detection Result'
                : 'Risk Detection'}
            </h3>

            {!activeDetector && (
              <p className="text-gray-500 text-xs">Select a detector from the left panel.</p>
            )}

            {detectorLoading && (
              <div className="text-center text-gray-400 py-8">
                <div className="text-2xl animate-spin mb-2">⚙️</div>
                <div className="text-xs">Running detector…</div>
              </div>
            )}

            {detectorError && (
              <div className="bg-red-900/50 border border-red-700 text-red-300 text-xs rounded p-2">
                {detectorError}
              </div>
            )}

            {suspectStatus && (
              <div className={`text-xs px-2 py-1 rounded mb-2 ${suspectStatus.found ? 'bg-green-900/50 text-green-300' : 'bg-yellow-900/50 text-yellow-300'}`}>
                {suspectStatus.found
                  ? `✓ "${suspectStatus.name}" ditemukan & disorot`
                  : `⚠ "${suspectStatus.name}" tidak ada di graph ini`}
              </div>
            )}

            {detectorResult && !detectorLoading && (
              <DetectorResultPanel
                result={detectorResult}
                focusedNodeId={focusedNodeId}
                onSuspectDoubleClick={(name: string, officerId?: number) => {
                  // Try direct officer node ID first, then fallback to name match
                  const candidateId = officerId ? `OFFICER:${officerId}` : null;
                  const match =
                    (candidateId ? nodes.find(n => n.id === candidateId) : null) ||
                    nodes.find(n => (n.data as NetworkNode).name.toLowerCase() === name.toLowerCase()) ||
                    nodes.find(n => (n.data as NetworkNode).name.toLowerCase().includes(name.toLowerCase().split(' ')[0]));

                  if (match) {
                    setFocusedNodeId(prev => prev === match.id ? null : match.id);
                    setSuspectStatus({ name, found: true });
                  } else {
                    setFocusedNodeId(null);
                    setSuspectStatus({ name, found: false });
                  }
                  setTimeout(() => setSuspectStatus(null), 3000);
                }}
              />
            )}
          </div>
        </aside>
      </div>
    </MainLayout>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PathAnalysisPanel({ data }: { data: Record<string, unknown> }) {
  if (data.error) return <div className="text-red-400 text-xs">{String(data.error)}</div>;
  if (!data.path) {
    return <div className="text-xs text-yellow-400">{String(data.message || 'No direct path found')}</div>;
  }
  const path = data.path as string[];
  return (
    <div className="space-y-2 text-xs">
      <div className="bg-blue-900/40 rounded p-2">
        <div className="text-gray-400">Hops</div>
        <div className="text-white text-lg font-bold">{data.hop_count as number}</div>
      </div>
      <div className="text-gray-400">Path: <span className="text-blue-300">{String(data.path_type || 'MIXED')}</span></div>
      <div className="space-y-1">
        {path.map((node, i) => (
          <div key={i} className="flex items-center gap-1">
            {i > 0 && <span className="text-gray-600">↓</span>}
            <span className="bg-gray-800 px-2 py-0.5 rounded text-gray-300 font-mono text-xs break-all">{node}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DetectorResultPanel({ result, focusedNodeId, onSuspectDoubleClick }: {
  result: DetectorResult;
  focusedNodeId?: string | null;
  onSuspectDoubleClick?: (name: string, officerId?: number) => void;
}) {
  const riskClass = RISK_COLOURS[result.risk_level || 'LOW'] || RISK_COLOURS.LOW;
  const score = result.risk_score ?? result.anomaly_score;

  return (
    <div className="space-y-3 text-xs">
      {result.risk_level && (
        <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold ${riskClass}`}>
          {result.risk_level.replace('_', ' ')}
          {score !== undefined && (
            <span className="ml-1 opacity-75">({(score as number).toFixed(2)})</span>
          )}
        </div>
      )}

      {result.summary && (
        <div className="bg-gray-800 rounded p-2 text-gray-300 leading-relaxed">{result.summary}</div>
      )}

      {Array.isArray(result.reason_codes) && result.reason_codes.length > 0 && (
        <div>
          <div className="text-gray-400 mb-1 font-medium">Reason codes</div>
          <div className="flex flex-wrap gap-1">
            {(result.reason_codes as string[]).map(code => (
              <span key={code} className="bg-yellow-900/40 text-yellow-300 px-2 py-0.5 rounded text-xs border border-yellow-700/40">
                {code}
              </span>
            ))}
          </div>
        </div>
      )}

      {Array.isArray(result.signals) && result.signals.length > 0 && (
        <div>
          <div className="text-gray-400 mb-1 font-medium">Signals</div>
          <div className="space-y-1">
            {(result.signals as { code: string; description: string; value?: number }[]).map((sig, i) => (
              <div key={i} className="bg-gray-800 rounded p-2">
                <div className="text-orange-300 font-medium">{sig.code}</div>
                <div className="text-gray-400">{sig.description}</div>
                {sig.value != null && <div className="text-gray-500">value: {sig.value}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {Array.isArray(result.suspects) && result.suspects.length > 0 && (
        <div>
          <div className="text-gray-400 mb-1 font-medium">
            Suspects ({(result.suspects as unknown[]).length})
            {onSuspectDoubleClick && <span className="text-gray-600 font-normal ml-1">· dbl-click to highlight</span>}
          </div>
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {(result.suspects as { officer_id?: number; name: string; position: string; entity_count: number; nominee_risk_score: number }[]).map((s, i) => {
              const nodeId = s.officer_id ? `OFFICER:${s.officer_id}` : null;
              const isActive = focusedNodeId !== null && focusedNodeId === nodeId;
              return (
                <div
                  key={i}
                  className={`rounded p-2 cursor-pointer transition-colors select-none ${
                    isActive ? 'bg-yellow-900/60 border border-yellow-500' : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                  onDoubleClick={() => onSuspectDoubleClick?.(s.name, s.officer_id)}
                  title="Double-click to highlight in graph"
                >
                  <div className={`font-medium ${isActive ? 'text-yellow-300' : 'text-white'}`}>{s.name}</div>
                  <div className="text-gray-400">{s.position} · {s.entity_count} entities</div>
                  <div className="text-red-400">Score: {s.nominee_risk_score}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {result.pyramid_nodes !== undefined && (
        <div className="bg-gray-800 rounded p-2 space-y-1">
          <div><span className="text-gray-400">Pyramid nodes:</span> <span className="text-white">{(result.pyramid_nodes as unknown[]).length}</span></div>
          <div><span className="text-gray-400">Controlled (&gt;25%):</span> <span className="text-white">{String(result.controlled_entities_count)}</span></div>
          <div><span className="text-gray-400">Max depth:</span> <span className="text-white">{String(result.max_chain_depth)}</span></div>
        </div>
      )}

      {result.cycles_found !== undefined && (
        <div className="bg-gray-800 rounded p-2">
          <div><span className="text-gray-400">Cycles found:</span> <span className={result.cycles_found ? 'text-red-400' : 'text-green-400'}>{String(result.cycles_found)}</span></div>
        </div>
      )}

      {Array.isArray(result.findings) && result.findings.length > 0 && (
        <div>
          <div className="text-gray-400 mb-1 font-medium">Findings ({(result.findings as unknown[]).length})</div>
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {(result.findings as { signal: string; description: string; confidence: number }[]).map((f, i) => (
              <div key={i} className="bg-gray-800 rounded p-2">
                <div className="text-blue-300 font-medium">{f.signal}</div>
                <div className="text-gray-300">{f.description}</div>
                <div className="text-gray-500">confidence: {f.confidence}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {Array.isArray(result.candidates) && result.candidates.length > 0 && (
        <div>
          <div className="text-gray-400 mb-1 font-medium">Candidates ({(result.candidates as unknown[]).length})</div>
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {(result.candidates as { name: string; confidence: number; inferred: boolean; effective_ownership_pct?: number }[]).map((c, i) => (
              <div key={i} className="bg-gray-800 rounded p-2">
                <div className="text-white font-medium">{c.name}</div>
                <div className="text-gray-400">{c.inferred ? '🔍 Inferred' : '✅ Direct'} · conf: {c.confidence}</div>
                {c.effective_ownership_pct !== undefined && (
                  <div className="text-gray-500">eff. ownership: {c.effective_ownership_pct}%</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
