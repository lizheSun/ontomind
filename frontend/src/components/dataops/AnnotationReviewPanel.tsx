import { useMemo, useState } from 'react';
import { App as AntApp, Button, Space, Table, Tag, Tooltip, Typography } from 'antd';
import { batchReviewAnnotations } from '../../services/metadata.service';
import type { Annotation } from '../../types/metadata';

const { Text } = Typography;

interface Props {
  items: Annotation[];
  onReview: (id: number, action: 'accept' | 'reject') => Promise<void>;
  onRefresh: () => Promise<void>;
}

export default function AnnotationReviewPanel({ items, onReview, onRefresh }: Props) {
  const { message } = AntApp.useApp();
  const [selected, setSelected] = useState<number[]>([]);
  const high = useMemo(() => items.filter((i) => i.confidence >= 0.8).map((i) => i.id), [items]);

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <Button size="small" onClick={() => setSelected(high)}>
          选中 ≥0.8
        </Button>
        <Button
          size="small"
          type="primary"
          disabled={!selected.length}
          onClick={async () => {
            await batchReviewAnnotations(selected, 'accept');
            message.success(`已采纳 ${selected.length} 条`);
            setSelected([]);
            await onRefresh();
          }}
        >
          批量采纳
        </Button>
      </Space>
      <Table
        size="small"
        rowKey="id"
        dataSource={items}
        rowSelection={{
          selectedRowKeys: selected,
          onChange: (keys) => setSelected(keys as number[]),
        }}
        columns={[
          { title: '目标', render: (_: unknown, r: Annotation) => `${r.target_type}#${r.target_id}` },
          { title: '类型', dataIndex: 'label_kind', width: 120 },
          { title: '建议值', dataIndex: 'label_value', ellipsis: true },
          {
            title: '置信度',
            dataIndex: 'confidence',
            width: 90,
            render: (v: number) => (
              <Tag color={v >= 0.85 ? 'green' : v >= 0.65 ? 'gold' : 'default'}>{v.toFixed(2)}</Tag>
            ),
          },
          { title: '来源', dataIndex: 'source', width: 70 },
          {
            title: '证据',
            dataIndex: 'evidence_json',
            render: (v: Record<string, unknown> | null) =>
              v ? (
                <Tooltip title={JSON.stringify(v)}>
                  <Text type="secondary">查看</Text>
                </Tooltip>
              ) : (
                '—'
              ),
          },
          {
            title: '操作',
            width: 140,
            render: (_: unknown, r: Annotation) => (
              <Space>
                <Button size="small" type="link" onClick={() => void onReview(r.id, 'accept')}>
                  采纳
                </Button>
                <Button size="small" type="link" danger onClick={() => void onReview(r.id, 'reject')}>
                  驳回
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </div>
  );
}
