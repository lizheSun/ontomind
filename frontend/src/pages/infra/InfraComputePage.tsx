/** Infra 电脑 — 对齐 Yao /dashboard/computers：标题 + 电脑/容器/服务 Tab。 */
import { useMemo } from 'react';
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';
import { DesktopOutlined } from '@ant-design/icons';
import { PageHeader } from '../../components/common/PageHeader';

const KINDS = [
  { key: 'nodes', label: '电脑', path: '/infra/compute/nodes' },
  { key: 'docker', label: '容器', path: '/infra/compute/docker' },
  { key: 'services', label: '服务', path: '/infra/compute/services' },
] as const;

export default function InfraComputePage() {
  const loc = useLocation();
  const nav = useNavigate();
  const { nodeId } = useParams();
  const isDetail = Boolean(nodeId);

  const kind = useMemo(() => {
    if (loc.pathname.includes('/docker')) return 'docker';
    if (loc.pathname.includes('/services')) return 'services';
    return 'nodes';
  }, [loc.pathname]);

  return (
    <div className="om-page om-computer page-enter">
      {!isDetail && (
        <>
          <PageHeader
            title={
              <>
                <DesktopOutlined style={{ color: 'var(--accent)' }} />
                电脑
              </>
            }
            desc="算力节点、容器与常驻服务。点卡片进入详情。"
          />
          <div className="om-comp-kinds">
            {KINDS.map((k) => (
              <button
                key={k.key}
                type="button"
                className={kind === k.key ? 'om-comp-kind active' : 'om-comp-kind'}
                onClick={() => nav(k.path)}
              >
                {k.label}
              </button>
            ))}
          </div>
        </>
      )}
      <Outlet />
    </div>
  );
}
