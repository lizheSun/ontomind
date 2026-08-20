import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { Alert, App as AntApp, Button, Form, Input, Modal, Select, Space, Spin } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { htmlToMarkdown } from '../../utils/htmlToMarkdown';
import { fetchWikiUrl, importWikiDocument } from '../../services/wiki.service';
import type { WikiSpace } from '../../types/wiki';

interface Props {
  open: boolean;
  spaces: WikiSpace[];
  defaultSpaceId?: number;
  onClose: () => void;
  onSaved: (docId: number) => void;
}

export default function UrlClipModal({ open, spaces, defaultSpaceId, onClose, onSaved }: Props) {
  const { message } = AntApp.useApp();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [markdown, setMarkdown] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const [title, setTitle] = useState('');
  const [spaceId, setSpaceId] = useState<number | undefined>(defaultSpaceId);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setUrl('');
      setMarkdown('');
      setWarnings([]);
      setTitle('');
      setSpaceId(defaultSpaceId ?? spaces[0]?.id);
    }
  }, [open, defaultSpaceId, spaces]);

  const fetch = async () => {
    if (!url.trim()) return;
    setLoading(true);
    try {
      const res = await fetchWikiUrl(url.trim());
      const result = htmlToMarkdown(res.html, { extractArticle: true });
      setMarkdown(result.markdown);
      setWarnings(result.warnings);
      setTitle(result.title || '');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '抓取失败');
    } finally {
      setLoading(false);
    }
  };

  const save = async () => {
    if (!markdown.trim()) {
      message.warning('请先抓取内容');
      return;
    }
    setSaving(true);
    try {
      const doc = await importWikiDocument({
        source_type: 'url',
        title: title || undefined,
        content_md: markdown,
        source_url: url,
        space_id: spaceId,
        status: 'draft',
      });
      message.success('已保存');
      onSaved(doc.id);
      onClose();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="从 URL 剪藏"
      open={open}
      onCancel={onClose}
      destroyOnHidden
      width={960}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={saving} onClick={() => void save()}>
            保存
          </Button>
        </Space>
      }
    >
      <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
        <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." />
        <Button type="primary" loading={loading} onClick={() => void fetch()}>
          抓取
        </Button>
      </Space.Compact>
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : markdown ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Editor
            height={300}
            language="markdown"
            theme="vs"
            value={markdown}
            onChange={(v) => setMarkdown(v ?? '')}
            options={{ minimap: { enabled: false }, fontSize: 12, wordWrap: 'on' }}
          />
          <div
            style={{
              height: 300,
              overflow: 'auto',
              border: '1px solid rgba(0,0,0,0.06)',
              borderRadius: 8,
              padding: 12,
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
          </div>
        </div>
      ) : null}
      {warnings.map((w) => (
        <Alert key={w} type="warning" showIcon style={{ marginTop: 8 }} message={w} />
      ))}
      <Form layout="vertical" style={{ marginTop: 12 }}>
        <Form.Item label="标题">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} />
        </Form.Item>
        <Form.Item label="空间">
          <Select
            value={spaceId}
            onChange={setSpaceId}
            options={spaces.map((s) => ({ value: s.id, label: s.name }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
