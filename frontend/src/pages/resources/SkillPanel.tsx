/**
 * SkillPanel — 技能模块面板 (T49 Wave 10)
 *
 * 5 层导航第 4 层：给智能体加载的能力模块，对应 opencode
 * `~/.config/opencode/skills/*` 目录里的 SKILL.md 定义。
 */
import { useCallback, useEffect, useState } from 'react';
import { App, Button, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ApiOutlined,
  CloudUploadOutlined,
  CodeOutlined,
  LinkOutlined,
  ReloadOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import {
  DangerConfirm,
  DataTable,
  TagPill,
} from '../../components/common';
import { resourcesAPI } from '../../services';
import type { Skill } from '../../types';

interface SkillPanelProps {
  onCountChange?: (count: number) => void;
}

const TYPE_LABELS: Record<Skill['skill_type'], string> = {
  docker: 'Docker',
  mcp: 'MCP',
  script: '脚本',
  api: 'API',
};

const TYPE_COLORS: Record<
  Skill['skill_type'],
  'emerald' | 'purple' | 'amber' | 'blue'
> = {
  docker: 'emerald',
  mcp: 'purple',
  script: 'amber',
  api: 'blue',
};

const TYPE_ICON: Record<Skill['skill_type'], React.ReactNode> = {
  docker: <ToolOutlined />,
  mcp: <LinkOutlined />,
  script: <CodeOutlined />,
  api: <ApiOutlined />,
};

export default function SkillPanel({ onCountChange }: SkillPanelProps) {
  const { message } = App.useApp();
  const [items, setItems] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [installingId, setInstallingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await resourcesAPI.listSkills({ skip: 0, limit: 200 });
      const list: Skill[] = res.data?.data ?? [];
      setItems(list);
      onCountChange?.(list.length);
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '加载 Skill 失败',
      );
    } finally {
      setLoading(false);
    }
  }, [message, onCountChange]);

  useEffect(() => {
    load();
  }, [load]);

  const handleInstall = async (row: Skill) => {
    setInstallingId(row.id);
    try {
      await resourcesAPI.installSkill(row.id);
      message.success('安装成功');
      await load();
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '安装失败',
      );
    } finally {
      setInstallingId(null);
    }
  };

  const handleDelete = (row: Skill) => {
    DangerConfirm({
      title: `确认删除 Skill “${row.name}”？`,
      onOk: async () => {
        try {
          await resourcesAPI.deleteSkill(row.id);
          message.success('已删除');
          await load();
        } catch (err) {
          message.error(err instanceof Error ? err.message : '删除失败');
        }
      },
    });
  };

  const columns: ColumnsType<Skill> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string, row) => (
        <Space size={6}>
          <span style={{ color: '#a78bfa', fontSize: 14 }}>
            {TYPE_ICON[row.skill_type] ?? <ToolOutlined />}
          </span>
          <span style={{ color: '#e8eef5', fontWeight: 500 }}>{v}</span>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'skill_type',
      key: 'skill_type',
      width: 120,
      render: (t: Skill['skill_type']) => (
        <TagPill color={TYPE_COLORS[t] ?? 'blue'}>
          {TYPE_LABELS[t] ?? t}
        </TagPill>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 200,
      render: (tags?: string[]) =>
        tags && tags.length > 0 ? (
          <Space size={4} wrap>
            {tags.slice(0, 3).map((t) => (
              <Tag key={t} style={{ fontSize: 11 }}>{t}</Tag>
            ))}
          </Space>
        ) : (
          '-'
        ),
    },
    {
      title: '安装状态',
      dataIndex: 'is_installed',
      key: 'is_installed',
      width: 110,
      render: (installed: boolean) =>
        installed ? (
          <Tag color="success">已安装</Tag>
        ) : (
          <Tag>未安装</Tag>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, row) => (
        <Space size={0}>
          {!row.is_installed && (
            <Button
              type="link"
              size="small"
              icon={<CloudUploadOutlined />}
              loading={installingId === row.id}
              onClick={() => handleInstall(row)}
            >
              安装
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDelete(row)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 8,
          marginBottom: 12,
        }}
      >
        <Button
          icon={<ReloadOutlined />}
          onClick={load}
          loading={loading}
        >
          刷新
        </Button>
      </div>
      <DataTable<Skill>
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        emptyTitle="暂无 Skill"
        emptyDescription="Skill 由「一键发现」自动同步自 ~/.config/opencode/skills/"
      />
    </div>
  );
}
