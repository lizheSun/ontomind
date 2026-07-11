import { useEffect, useState } from 'react';
import { Select, Space, Tag } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import { agentLooperService } from '../../services/agentLooper.service';
import { resourcesAPI } from '../../services';
import type { AgentLooperListEntry } from '../../types/agentLooper';

export interface AgentPickerProps {
  value?: number | null | undefined;
  onChange?: (value: number | null | undefined) => void;
  placeholder?: string;
  size?: 'small' | 'middle' | 'large';
  style?: React.CSSProperties;
  includePlatformLlm?: boolean;
  includeLegacyAgents?: boolean;
}

export default function AgentPicker({
  value,
  onChange,
  placeholder = '选择 Agent',
  size = 'small',
  style,
  includePlatformLlm = true,
  includeLegacyAgents = true,
}: AgentPickerProps) {
  const [loopers, setLoopers] = useState<AgentLooperListEntry[]>([]);
  const [legacyAgents, setLegacyAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      agentLooperService.list().catch(() => [] as AgentLooperListEntry[]),
      includeLegacyAgents
        ? resourcesAPI.listAgents({ skip: 0, limit: 200 }).catch(() => [])
        : Promise.resolve([]),
    ])
      .then(([l, a]) => {
        setLoopers(l);
        const raw = Array.isArray(a) ? a : ((a as any)?.data?.data ?? []);
        setLegacyAgents(raw);
      })
      .finally(() => setLoading(false));
  }, [includeLegacyAgents]);

  const options: { value: string; label: React.ReactNode }[] = [];

  if (includePlatformLlm) {
    options.push({
      value: 'platform_llm',
      label: (
        <Space>
          <RobotOutlined /> 平台 LLM
        </Space>
      ),
    });
  }

  loopers.forEach((l) => {
    options.push({
      value: `looper_${l.id}`,
      label: (
        <Space size={4}>
          <Tag
            color={l.type === 'opencode_native' ? 'purple' : 'blue'}
            style={{ marginRight: 0, fontSize: 10 }}
          >
            {l.type === 'opencode_native' ? '原生' : '定制'}
          </Tag>
          {l.name}
          {l.model && (
            <span style={{ color: '#8895b4', fontSize: 11 }}>{l.model}</span>
          )}
        </Space>
      ),
    });
  });

  legacyAgents.forEach((a: any) => {
    const aid = a.id;
    if (!loopers.find((l) => l.name === a.name)) {
      options.push({
        value: `legacy_${aid}`,
        label: (
          <Space size={4}>
            <Tag color="default" style={{ marginRight: 0, fontSize: 10 }}>
              遗留
            </Tag>
            {a.name}
          </Space>
        ),
      });
    }
  });

  const handleChange = (v: string) => {
    if (v === 'platform_llm') {
      onChange?.(null);
    } else if (v.startsWith('looper_')) {
      onChange?.(Number(v.replace('looper_', '')));
    } else if (v.startsWith('legacy_')) {
      onChange?.(Number(v.replace('legacy_', '')));
    }
  };

  const currentValue =
    value === null || value === undefined ? 'platform_llm' : `looper_${value}`;

  return (
    <Select<string>
      size={size}
      style={{ minWidth: 180, ...style }}
      placeholder={placeholder}
      value={currentValue}
      onChange={handleChange}
      loading={loading}
      options={options}
      allowClear={false}
    />
  );
}
