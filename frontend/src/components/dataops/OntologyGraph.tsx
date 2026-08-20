import { useEffect, useMemo } from 'react';
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { GraphData } from '../../types/ontology';

function layout(data: GraphData): { nodes: Node[]; edges: Edge[] } {
  const depth = new Map<string, number>();
  const byKey = new Map(data.nodes.map((n) => [n.key, n]));
  const calc = (key: string, seen = new Set<string>()): number => {
    if (depth.has(key)) return depth.get(key)!;
    if (seen.has(key)) return 0;
    seen.add(key);
    const n = byKey.get(key);
    const d = n?.parent ? calc(n.parent, seen) + 1 : 0;
    depth.set(key, d);
    return d;
  };
  data.nodes.forEach((n) => calc(n.key));
  const layers = new Map<number, string[]>();
  depth.forEach((d, key) => {
    if (!layers.has(d)) layers.set(d, []);
    layers.get(d)!.push(key);
  });

  const nodes: Node[] = data.nodes.map((n) => {
    const d = depth.get(n.key) || 0;
    const row = layers.get(d) || [];
    const idx = row.indexOf(n.key);
    const draft = n.status === 'draft';
    return {
      id: n.key,
      position: { x: idx * 220 + 40, y: d * 140 + 40 },
      data: {
        label: `${n.label || n.key}${draft ? ' (draft)' : ''}`,
      },
      style: {
        opacity: draft ? 0.55 : 1,
        borderStyle: (n.confidence ?? 1) < 0.85 ? 'dashed' : 'solid',
        borderWidth: 1.5,
        borderColor: draft ? '#faad14' : '#0071e3',
        borderRadius: 8,
        padding: 10,
        fontSize: 12,
        background: '#fff',
        width: 170,
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
      },
    };
  });

  const edges: Edge[] = data.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.cardinality || e.label,
    style: { opacity: e.status === 'draft' ? 0.45 : 0.9, stroke: '#86868b' },
    labelStyle: { fontSize: 10, fill: '#6e6e73' },
  }));

  return { nodes, edges };
}

export default function OntologyGraph({
  data,
  refreshKey,
}: {
  data: GraphData;
  refreshKey?: string | number;
}) {
  const laid = useMemo(() => layout(data), [data]);
  const [nodes, setNodes, onNodesChange] = useNodesState(laid.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(laid.edges);

  useEffect(() => {
    setNodes(laid.nodes);
    setEdges(laid.edges);
  }, [laid, setNodes, setEdges, refreshKey]);

  if (!data.nodes.length) {
    return (
      <div
        style={{
          height: '100%',
          minHeight: 360,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#86868b',
          background: '#fafafa',
          borderRadius: 12,
        }}
      >
        暂无图数据。请先「构建本体」。
      </div>
    );
  }

  return (
    <div style={{ height: '100%', minHeight: 420, background: '#fafafa', borderRadius: 12 }}>
      <ReactFlow
        key={String(refreshKey ?? data.nodes.length)}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}
