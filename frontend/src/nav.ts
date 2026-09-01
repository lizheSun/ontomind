/**
 * 平台导航目录 — AppLayout / CmdK 共用，避免两处漂移。
 * 结构参照 Yao Desktop：图标轨（域）+ 侧栏（子项）。
 */
export interface NavChild {
  key: string;
  label: string;
  keywords?: string[];
}

export interface NavItem {
  key: string;
  label: string;
  children?: NavChild[];
  keywords?: string[];
}

export interface DomainDef {
  key: string;
  label: string;
  hint: string;
  color: string;
  keywords: string[];
  sub: NavItem[];
}

/** 对齐 Yao `chatbox-main-menu` 实测宽度 */
export const RAIL_W = 64;
/** 对齐 Yao 中间 context 栏实测宽度 */
export const SIDEBAR_W = 256;

export const DOMAINS: DomainDef[] = [
  { key: 'overview', label: '总览', hint: 'Mission Control', color: '#8B95A7', keywords: ['overview', 'mission', '总览'], sub: [] },
  {
    key: 'chat',
    label: '会话',
    hint: 'OpenCode / DSH',
    color: '#3371fc',
    keywords: ['chat', '会话', 'opencode', 'dsh', 'harness', '对话'],
    sub: [],
  },
  {
    key: 'board',
    label: '看板',
    hint: '任务与会话',
    color: '#3371fc',
    keywords: ['board', 'kanban', '看板', '任务', 'task'],
    sub: [],
  },
  {
    key: 'codeops',
    label: 'CodeOps',
    hint: '编码与流水线',
    color: '#4F8CFF',
    keywords: ['code', 'git', 'ci', '编码'],
    sub: [
      { key: '/codeops/workspace', label: '编码工作台', keywords: ['workspace', 'ide'] },
      { key: '/codeops/pipelines', label: 'CI/CD 流水线', keywords: ['pipeline', 'cicd'] },
    ],
  },
  {
    key: 'dataops',
    label: 'DataOps',
    hint: '数据与本体',
    color: '#3DDC97',
    keywords: ['data', 'warehouse', 'ontology', '数据'],
    sub: [
      {
        key: '/dataops/catalog',
        label: '资产地图',
        children: [
          { key: '/dataops/catalog/biz-systems', label: '元数据与标注' },
          { key: '/dataops/catalog/warehouse', label: '数据仓库' },
          { key: '/dataops/catalog/ontology', label: '本体建模' },
          { key: '/dataops/catalog/etl', label: 'ETL代码库' },
          { key: '/dataops/catalog/code', label: '业务代码库' },
          { key: '/dataops/catalog/knowledge', label: '知识库' },
          { key: '/dataops/catalog/smart-dev', label: '智能数开' },
        ],
      },
      { key: '/dataops/lineage', label: '数据血缘' },
      { key: '/dataops/quality', label: '数据质量' },
    ],
  },
  {
    key: 'modelops',
    label: 'ModelOps',
    hint: '实验与推理',
    color: '#A78BFA',
    keywords: ['model', 'llm', '推理', '实验'],
    sub: [
      { key: '/modelops/experiments', label: '实验管理' },
      { key: '/modelops/gateway', label: '推理网关' },
      { key: '/modelops/monitoring', label: '模型监控' },
    ],
  },
  {
    key: 'agentops',
    label: 'AgentOps',
    hint: 'Agent / Skill',
    color: '#F5C14A',
    keywords: ['agent', 'skill', 'bundle', '机器人'],
    sub: [
      { key: '/agentops/agents', label: 'Agent 设计' },
      { key: '/agentops/skills', label: 'Skill 设计' },
      { key: '/agentops/bundles', label: '编排方案' },
      { key: '/agentops/deploy', label: '发布中心' },
    ],
  },
  {
    key: 'govops',
    label: 'GovOps',
    hint: '治理与成本',
    color: '#F07178',
    keywords: ['gov', 'llm', 'security', '合规'],
    sub: [
      { key: '/govops/llm', label: 'LLM 配置' },
      { key: '/govops/catalog', label: '资产目录' },
      { key: '/govops/security', label: '安全合规' },
      { key: '/govops/cost', label: '成本归因' },
    ],
  },
  {
    key: 'infra',
    label: 'Infra',
    hint: '电脑与 AIDE',
    color: '#5EEAD4',
    keywords: ['infra', 'docker', 'aide', 'opencode', '节点', '电脑', 'computer'],
    sub: [
      { key: '/infra/compute', label: '电脑', keywords: ['node', 'docker', 'container', '电脑', '节点', '容器'] },
      { key: '/infra/aide', label: 'AIDE' },
    ],
  },
];

export function domainHome(d: DomainDef): string {
  if (!d.sub.length) return `/${d.key}`;
  const first = d.sub[0];
  if (first.children && first.children.length > 0) return first.children[0].key;
  return first.key;
}

export function findDomain(pathname: string): DomainDef {
  const p = pathname.split('/')[1] || 'overview';
  return DOMAINS.find((d) => d.key === p) || DOMAINS[0];
}

export function flattenNav(): { key: string; label: string; domain: string; keywords: string[] }[] {
  const out: { key: string; label: string; domain: string; keywords: string[] }[] = [];
  for (const d of DOMAINS) {
    if (!d.sub.length) {
      out.push({ key: `/${d.key}`, label: d.label, domain: d.key, keywords: d.keywords });
      continue;
    }
    for (const s of d.sub) {
      if (s.children?.length) {
        for (const c of s.children) {
          out.push({
            key: c.key,
            label: `${d.label} / ${c.label}`,
            domain: d.key,
            keywords: [...d.keywords, c.label, ...(c.keywords ?? [])],
          });
        }
      } else {
        out.push({
          key: s.key,
          label: `${d.label} / ${s.label}`,
          domain: d.key,
          keywords: [...d.keywords, s.label, ...(s.keywords ?? [])],
        });
      }
    }
  }
  out.push({
    key: '/users',
    label: '用户管理',
    domain: 'users',
    keywords: ['users', 'user', '用户', '账号'],
  });
  return out;
}
