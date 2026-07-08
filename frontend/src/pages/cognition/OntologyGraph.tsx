import { useEffect, useMemo, useRef } from 'react';
import { Graph } from '@antv/g6';

const PALETTE = [
  '#60a5fa', '#a78bfa', '#f472b6', '#fbbf24', '#34d399', '#22d3ee',
  '#c084fc', '#fb7185', '#a3e635', '#38bdf8', '#facc15', '#e879f9',
  '#2dd4bf', '#fda4af',
];

const DOMAIN_COLORS: Record<string, string> = {
  用户: '#3b82f6', 订单: '#8b5cf6', 商品: '#34d399', 支付: '#f59e0b',
  营销: '#ec4899', 库存: '#22d3ee', 财务: '#a78bfa', 客服: '#22d3ee',
  通用: '#60a5fa',
};

function hashColor(s?: string): string {
  if (!s) return '#64748b';
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

function colorOf(domain?: string, label?: string): string {
  if (domain && DOMAIN_COLORS[domain]) return DOMAIN_COLORS[domain];
  return hashColor(label || domain);
}

/**
 * 位置策略（贴合截图布局）：
 *  - 孤立节点（无边）：上方按 9 列网格平铺（见截图）；
 *  - 有连接节点：先不指定 x/y，由 d3-force 在下方自然展开为网络图。
 *
 *  两阶段渲染：
 *  1) 第一次 setData：仅放孤立节点（style.x/y 固定），d3-force 对少量规则节点不改变位置；
 *  2) 第二次 setData：补齐连接节点，由 d3-force 自由排布；布局完成后 fitView。
 */
function gridPositions(
  ids: string[],
  cols: number,
  startX: number,
  startY: number,
  cellW: number,
  cellH: number,
): Record<string, { x: number; y: number }> {
  const pos: Record<string, { x: number; y: number }> = {};
  ids.forEach((id, i) => {
    pos[id] = { x: startX + (i % cols) * cellW, y: startY + Math.floor(i / cols) * cellH };
  });
  return pos;
}

export default function OntologyGraph({
  data,
  onNodeClick,
}: {
  data: { nodes: any[]; edges: any[] } | null;
  onNodeClick?: (node: any) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const dataRef = useRef<{ nodes: any[]; edges: any[] } | null>(null);
  const clickRef = useRef<((n: any) => void) | undefined>(undefined);
  clickRef.current = onNodeClick;
  dataRef.current = data;

  // 分组 + 网格位置
  const plan = useMemo(() => {
    const nodes = data?.nodes || [];
    const edges = data?.edges || [];
    const degree: Record<string, number> = {};
    edges.forEach((e) => {
      degree[e.source] = (degree[e.source] || 0) + 1;
      degree[e.target] = (degree[e.target] || 0) + 1;
    });
    const isolated = nodes.filter((n) => !degree[n.id]);
    const connected = nodes.filter((n) => degree[n.id]);

    const cols = 9;
    const cellW = 132;
    const cellH = 92;
    const startX = 60;
    const startY = 60;
    const isolatedPos = gridPositions(
      isolated.map((n) => n.id),
      cols,
      startX,
      startY,
      cellW,
      cellH,
    );
    const isolatedRows = Math.ceil(isolated.length / cols) || 1;
    const gridBottom = startY + isolatedRows * cellH;
    return { isolated, connected, edges, isolatedPos, gridBottom, cols, cellW, cellH };
  }, [data]);

  const legend = useMemo(() => {
    const map = new Map<string, { color: string; count: number }>();
    (data?.nodes || []).forEach((n) => {
      const d = n.domain || '(未分类)';
      const color = colorOf(n.domain, n.local_name || n.label);
      const cur = map.get(d);
      if (cur) cur.count += 1;
      else map.set(d, { color, count: 1 });
    });
    return Array.from(map.entries()).map(([name, v]) => ({ name, ...v }));
  }, [data]);

  const buildIsolated = () => ({
    nodes: plan.isolated.map((n) => {
      const p = plan.isolatedPos[n.id];
      return {
        id: n.id,
        data: {
          label: n.local_name || n.label,
          definition: n.definition || n.label,
          domain: n.domain,
          entityType: n.entity_type,
          attrCount: n.attr_count,
        },
        style: { x: p.x, y: p.y },
      };
    }),
    edges: [] as any[],
  });

  const buildConnected = () => ({
    nodes: plan.connected.map((n) => ({
      id: n.id,
      data: {
        label: n.local_name || n.label,
        definition: n.definition || n.label,
        domain: n.domain,
        entityType: n.entity_type,
        attrCount: n.attr_count,
      },
      // 不写 x/y：交给 d3-force
    })),
    edges: plan.edges.map((e) => ({
      source: e.source,
      target: e.target,
      data: { label: e.label },
    })),
  });

  const commonNodeStyle: any = {
    size: (d: any) => 26 + Math.min((d.data?.attrCount || 0) * 2, 16),
    fill: (d: any) => colorOf(d.data?.domain, d.data?.label),
    stroke: (d: any) =>
      d.data?.entityType === 'enumeration' ? '#fbbf24' : 'rgba(255,255,255,0.35)',
    lineWidth: 1.5,
    labelText: (d: any) => d.data?.label || d.id,
    labelFill: '#e8eef5',
    labelFontSize: 10,
    labelFontWeight: 600,
    labelPlacement: 'bottom',
    labelOffsetY: 4,
    labelBackground: true,
    labelBackgroundFill: 'rgba(10,15,31,0.85)',
    labelBackgroundRadius: 3,
    cursor: 'pointer',
  };

  const commonEdgeStyle: any = {
    stroke: '#5a6b85',
    lineWidth: 1.2,
    endArrow: true,
    endArrowSize: 8,
    labelText: (d: any) => d.data?.label || '',
    labelFill: '#9aa7bd',
    labelFontSize: 9,
    labelBackground: true,
    labelBackgroundFill: 'rgba(10,15,31,0.85)',
    labelBackgroundRadius: 2,
  };

  const fitSafely = (graph: any) => {
    if (!graph || graph.destroyed) return;
    try {
      graph.fitView({ when: 'always' });
    } catch {
      /* ignore */
    }
  };

  // 初始化
  useEffect(() => {
    if (!containerRef.current) return;
    let graph: any;
    try {
      graph = new Graph({
        container: containerRef.current,
        autoResize: false,
        background: '#070b1a',
        data: { nodes: [], edges: [] },
        node: { style: commonNodeStyle },
        edge: { style: commonEdgeStyle },
        layout: {
          type: 'd3-force',
          link: { distance: 120 },
          manyBody: { strength: -120 },
          preventOverlap: true,
          nodeSize: 60,
        },
        behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
      });
      graphRef.current = graph;

      graph.on('node:click', (e: any) => {
        const id = e?.target?.id;
        if (!id) return;
        const node = (dataRef.current?.nodes || []).find((n) => n.id === id);
        clickRef.current?.(node);
      });

      const d = dataRef.current;
      if (d && (d.nodes || []).length > 0) {
        // 阶段 1：仅孤立节点
        graph.setData(buildIsolated());
        graph.render()
          .then(() => {
            if (graph.destroyed) return;
            // 阶段 2：补齐连接节点
            graph.setData({
              nodes: [...buildIsolated().nodes, ...buildConnected().nodes],
              edges: buildConnected().edges,
            });
            return graph.render();
          })
          .then(() => {
            if (!graph.destroyed) {
              setTimeout(() => fitSafely(graph), 50);
            }
          })
          .catch(() => {});
      }
    } catch {}

    return () => {
      try {
        graph?.destroy();
      } catch {}
      graphRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 数据更新：复用实例
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph || graph.destroyed) return;
    if (!data || (data.nodes || []).length === 0) {
      graph.setData({ nodes: [], edges: [] });
      graph.render().catch(() => {});
      return;
    }
    const isolatedData = buildIsolated();
    const connectedData = buildConnected();
    graph.setData({
      nodes: [...isolatedData.nodes, ...connectedData.nodes],
      edges: connectedData.edges,
    });
    graph.render()
      .then(() => {
        if (!graph.destroyed) setTimeout(() => fitSafely(graph), 50);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      {legend.length > 0 && (
        <div
          style={{
            position: 'absolute',
            left: 12,
            top: 12,
            maxWidth: 240,
            padding: '8px 10px',
            background: 'rgba(10,15,31,0.72)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8,
            backdropFilter: 'blur(4px)',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '4px 10px',
          }}
        >
          {legend.slice(0, 16).map((it) => (
            <span
              key={it.name}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                fontSize: 11,
                color: '#94a3b8',
              }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 8,
                  background: it.color,
                  display: 'inline-block',
                }}
              />
              {it.name}{' '}
              <span style={{ color: '#506380' }}>{it.count}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
