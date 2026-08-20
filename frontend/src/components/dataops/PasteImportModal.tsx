import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { Alert, App as AntApp, Button, Form, Input, Modal, Select, Space } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { htmlToMarkdown, markdownFromPlainText } from '../../utils/htmlToMarkdown';
import { importWikiDocument } from '../../services/wiki.service';
import type { WikiSpace } from '../../types/wiki';

interface Props {
  open: boolean;
  spaces: WikiSpace[];
  defaultSpaceId?: number;
  onClose: () => void;
  onSaved: (docId: number) => void;
}

export default function PasteImportModal({ open, spaces, defaultSpaceId, onClose, onSaved }: Props) {
  const { message } = AntApp.useApp();
  const [markdown, setMarkdown] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const [title, setTitle] = useState('');
  const [spaceId, setSpaceId] = useState<number | undefined>(defaultSpaceId);
  const [tags, setTags] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setSpaceId(defaultSpaceId ?? spaces[0]?.id);
      setMarkdown('');
      setWarnings([]);
      setTitle('');
      setTags('');
      setSourceUrl('');
    }
  }, [open, defaultSpaceId, spaces]);

  const onPaste = (e: React.ClipboardEvent<HTMLDivElement>) => {
    e.preventDefault();
    const html = e.clipboardData.getData('text/html');
    const plain = e.clipboardData.getData('text/plain');
    if (html) {
      const result = htmlToMarkdown(html, { extractArticle: false });
      setMarkdown(result.markdown);
      setWarnings(result.warnings);
      if (result.title) setTitle(result.title);
    } else {
      setMarkdown(markdownFromPlainText(plain));
      setWarnings([]);
    }
  };

  const save = async () => {
    if (!markdown.trim()) {
      message.warning('请先粘贴内容');
      return;
    }
    setSaving(true);
    try {
      const doc = await importWikiDocument({
        source_type: 'paste',
        title: title || undefined,
        content_md: markdown,
        source_url: sourceUrl || undefined,
        space_id: spaceId,
        tags: tags
          .split(/[,，]/)
          .map((t) => t.trim())
          .filter(Boolean),
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
      title="粘贴导入"
      open={open}
      onCancel={onClose}
      destroyOnHidden
      width={960}
      mask={{ closable: false }}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={saving} onClick={() => void save()}>
            保存
          </Button>
        </Space>
      }
    >
      {!markdown ? (
        <div
          contentEditable
          suppressContentEditableWarning
          onPaste={onPaste}
          style={{
            minHeight: 160,
            border: '1px dashed rgba(0,0,0,0.15)',
            borderRadius: 12,
            padding: 16,
            color: 'var(--text-secondary, #6e6e73)',
            outline: 'none',
          }}
        >
          Ctrl/Cmd+V 粘贴企业微信文档 / Word / PPT / 网页内容
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Editor
            height={320}
            language="markdown"
            theme="vs"
            value={markdown}
            onChange={(v) => setMarkdown(v ?? '')}
            options={{ minimap: { enabled: false }, fontSize: 12, wordWrap: 'on' }}
          />
          <div
            style={{
              height: 320,
              overflow: 'auto',
              border: '1px solid rgba(0,0,0,0.06)',
              borderRadius: 8,
              padding: 12,
              background: '#fff',
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
          </div>
        </div>
      )}
      {warnings.map((w) => (
        <Alert key={w} type="warning" showIcon style={{ marginTop: 8 }} message={w} />
      ))}
      <Form layout="vertical" style={{ marginTop: 12 }}>
        <Form.Item label="标题">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="自动从 H1 猜测" />
        </Form.Item>
        <Form.Item label="空间">
          <Select
            value={spaceId}
            onChange={setSpaceId}
            options={spaces.map((s) => ({ value: s.id, label: s.name }))}
          />
        </Form.Item>
        <Form.Item label="标签">
          <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="逗号分隔" />
        </Form.Item>
        <Form.Item label="来源 URL">
          <Input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
