/**
 * ComputePage — 算力调度主页面.
 * 两个 tab：docker 服务管理 + 调度任务管理.
 */
import { useState } from 'react';
import { Tabs } from 'antd';
import DockerServicePanel from './DockerServicePanel';
import ScheduleTaskPanel from './ScheduleTaskPanel';

export default function ComputePage() {
  const [tab, setTab] = useState<'docker' | 'tasks'>('docker');

  return (
    <div style={{ maxWidth: 1600, margin: '0 auto', padding: '8px 16px 24px' }}>
      <div
        style={{
          padding: '24px 4px 12px',
          borderBottom: '1px solid var(--border-hairline)',
          marginBottom: 12,
        }}
      >
        <h1
          style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 34,
            fontWeight: 500,
            letterSpacing: '-0.02em',
            margin: 0,
            color: 'var(--ink-100)',
            fontStyle: 'italic',
          }}
        >
          算力调度
        </h1>
        <p style={{ color: 'var(--ink-60)', fontSize: 13, marginTop: 6, marginBottom: 0 }}>
          管理 opencode docker 服务、编排定时/一次性任务、查看运行日志。
        </p>
      </div>

      <Tabs
        activeKey={tab}
        onChange={(k) => setTab(k as 'docker' | 'tasks')}
        size="large"
        items={[
          {
            key: 'docker',
            label: 'Docker 服务',
            children: <DockerServicePanel />,
          },
          {
            key: 'tasks',
            label: '调度任务',
            children: <ScheduleTaskPanel />,
          },
        ]}
      />
    </div>
  );
}