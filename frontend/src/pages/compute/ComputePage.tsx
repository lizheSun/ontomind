/**
 * ComputePage — 算力调度.
 * Tab 1: Docker 服务（节点挂载 / 镜像管理 / 容器管理）
 * Tab 2: 调度运行（任务定义 / 运行记录 / 日志查看）
 * Tab 3: 本地服务（OpenCode Web 启停 / CLI 执行 / 对话工作台选服务）
 */
import { useState } from 'react';
import { Tabs } from 'antd';
import ResourcesPanel from './ResourcesPanel';
import SchedulerPanel from './SchedulerPanel';
import OpenCodePanel from './OpenCodePanel';
import './compute.css';

type TabKey = 'resources' | 'scheduler' | 'opencode';

export default function ComputePage() {
  const [tab, setTab] = useState<TabKey>('resources');
  /* 懒挂载：首次切换到某 tab 才挂载对应面板，之后保持挂载以保留本地状态 */
  const [visited, setVisited] = useState({ resources: true, scheduler: false, opencode: false });

  const switchTab = (k: string) => {
    const key = k as TabKey;
    setTab(key);
    setVisited((v) => (v[key] ? v : { ...v, [key]: true }));
  };

  return (
    <div className="page-enter" style={{ maxWidth: 1600, margin: '0 auto', padding: '0 20px 28px' }}>
      <div className="compute-header">
        <h1>算力调度</h1>
        <span className="compute-header-desc">算力节点挂载 · Docker 容器管理 · 任务调度与运行日志 · 本地 OpenCode 服务</span>
        <Tabs
          className="compute-tabs"
          activeKey={tab}
          onChange={switchTab}
          items={[
            { key: 'resources', label: 'Docker 服务' },
            { key: 'scheduler', label: '调度运行' },
            { key: 'opencode', label: '本地服务' },
          ]}
        />
      </div>

      {visited.resources && (
        <div style={{ display: tab === 'resources' ? 'block' : 'none' }}>
          <ResourcesPanel />
        </div>
      )}
      {visited.scheduler && (
        <div style={{ display: tab === 'scheduler' ? 'block' : 'none' }}>
          <SchedulerPanel />
        </div>
      )}
      {visited.opencode && (
        <div style={{ display: tab === 'opencode' ? 'block' : 'none' }}>
          <OpenCodePanel />
        </div>
      )}
    </div>
  );
}
