/** Infra 算力管理 — 三级子路由由侧边栏切换，此处仅渲染 Outlet。 */
import { Outlet } from 'react-router-dom';

export default function InfraComputePage() {
  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '14px 16px' }}>
      <Outlet />
    </div>
  );
}