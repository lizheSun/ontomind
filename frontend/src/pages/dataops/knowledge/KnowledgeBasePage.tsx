import { useCallback, useEffect, useMemo, useState } from 'react';
import Editor from '@monaco-editor/react';
import {
  App as AntApp,
  Button,
  Empty,
  Input,
  List,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import {
  EditOutlined,
  FileTextOutlined,
  LinkOutlined,
  PlusOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import PasteImportModal from '../../../components/dataops/PasteImportModal';
import UrlClipModal from '../../../components/dataops/UrlClipModal';
import {
  getWikiDocument,
  listWikiDocuments,
  listWikiSpaces,
  listWikiVersions,
  rollbackWikiDocument,
  updateWikiDocument,
} from '../../../services/wiki.service';
import type { WikiDocument, WikiDocumentListItem, WikiDocumentVersion, WikiSpace } from '../../../types/wiki';

const { Text, Title } = Typography;

export default function KnowledgeBasePage() {
  const { message, modal } = AntApp.useApp();
  const [spaces, setSpaces] = useState<WikiSpace[]>([]);
  const [spaceId, setSpaceId] = useState<number | undefined>();
  const [docs, setDocs] = useState<WikiDocumentListItem[]>([]);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeId, setActiveId] = useState<number | undefined>();
  const [doc, setDoc] = useState<WikiDocument | null>(null);
  const [editing, setEditing] = useState(false);
  const [draftMd, setDraftMd] = useState('');
  const [versions, setVersions] = useState<WikiDocumentVersion[]>([]);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [urlOpen, setUrlOpen] = useState(false);
  const [metaOpen, setMetaOpen] = useState(true);

  const loadSpaces = useCallback(async () => {
    const rows = await listWikiSpaces();
    setSpaces(rows);
    setSpaceId((prev) => prev ?? rows[0]?.id);
  }, []);

  const loadDocs = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await listWikiDocuments({
        space_id: spaceId,
        keyword: keyword || undefined,
      });
      setDocs(rows);
    } finally {
      setLoading(false);
    }
  }, [spaceId, keyword]);

  useEffect(() => {
    void loadSpaces().catch((e) => message.error(e instanceof Error ? e.message : '加载空间失败'));
  }, [loadSpaces, message]);

  useEffect(() => {
    if (spaceId) void loadDocs();
  }, [spaceId, loadDocs]);

  const openDoc = async (id: number) => {
    setActiveId(id);
    setEditing(false);
    const d = await getWikiDocument(id);
    setDoc(d);
    setDraftMd(d.content_md || '');
    setVersions(await listWikiVersions(id));
  };

  const saveDoc = async () => {
    if (!doc) return;
    const updated = await updateWikiDocument(doc.id, {
      content_md: draftMd,
      change_note: '编辑保存',
    });
    setDoc(updated);
    setEditing(false);
    setVersions(await listWikiVersions(doc.id));
    message.success('已保存');
    void loadDocs();
  };

  const treeDocs = useMemo(() => docs.filter((d) => !d.parent_id || !docs.some((x) => x.id === d.parent_id)), [docs]);

  return (
    <div className="page-enter" style={{ height: 'calc(100vh - 52px)', display: 'flex', flexDirection: 'column', background: 'var(--bg-page, #F5F5F7)' }}>
      <div
        style={{
          height: 48,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          background: '#fff',
          borderBottom: '1px solid rgba(0,0,0,0.06)',
        }}
      >
        <Title level={5} style={{ margin: 0 }}>
          知识库
        </Title>
        <Space>
          <Button icon={<PlusOutlined />} onClick={() => setPasteOpen(true)}>
            粘贴导入
          </Button>
          <Button icon={<LinkOutlined />} onClick={() => setUrlOpen(true)}>
            从 URL 剪藏
          </Button>
          {doc ? (
            editing ? (
              <Button type="primary" icon={<SaveOutlined />} onClick={() => void saveDoc()}>
                保存
              </Button>
            ) : (
              <Button icon={<EditOutlined />} onClick={() => setEditing(true)}>
                编辑
              </Button>
            )
          ) : null}
          <Button type="text" onClick={() => setMetaOpen((v) => !v)}>
            {metaOpen ? '收起信息' : '展开信息'}
          </Button>
        </Space>
      </div>

      <div style={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: metaOpen ? '240px 1fr 280px' : '240px 1fr' }}>
        <div style={{ background: '#fff', borderRight: '1px solid rgba(0,0,0,0.06)', overflow: 'auto', padding: 12 }}>
          <Space orientation="vertical" style={{ width: '100%' }} size={8}>
            <SelectSpaces spaces={spaces} spaceId={spaceId} onChange={setSpaceId} />
            <Input.Search placeholder="搜索标题/正文" allowClear onSearch={setKeyword} onChange={(e) => !e.target.value && setKeyword('')} />
            {loading ? (
              <Spin />
            ) : treeDocs.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档" />
            ) : (
              <List
                size="small"
                dataSource={treeDocs}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      background: item.id === activeId ? 'rgba(0,113,227,0.08)' : undefined,
                      borderRadius: 8,
                      padding: '6px 8px',
                    }}
                    onClick={() => void openDoc(item.id)}
                  >
                    <Space>
                      <FileTextOutlined />
                      <Text ellipsis style={{ maxWidth: 160 }}>
                        {item.title}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            )}
          </Space>
        </div>

        <div style={{ background: '#fff', overflow: 'auto', padding: 16 }}>
          {!doc ? (
            <Empty description="选择或导入文档" style={{ marginTop: 80 }} />
          ) : editing ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, height: '100%' }}>
              <Editor
                height="100%"
                language="markdown"
                theme="vs"
                value={draftMd}
                onChange={(v) => setDraftMd(v ?? '')}
                options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: 'on' }}
              />
              <div style={{ overflow: 'auto', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 8, padding: 12 }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{draftMd}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <div>
              <Title level={3}>{doc.title}</Title>
              <Space size={6} style={{ marginBottom: 12 }}>
                <Tag>{doc.source_type}</Tag>
                <Tag>v{doc.current_version}</Tag>
                {(doc.tags || []).map((t) => (
                  <Tag key={t} color="blue">
                    {t}
                  </Tag>
                ))}
              </Space>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc.content_md}</ReactMarkdown>
            </div>
          )}
        </div>

        {metaOpen ? (
          <div style={{ background: '#fff', borderLeft: '1px solid rgba(0,0,0,0.06)', overflow: 'auto', padding: 12 }}>
            <Text strong>元信息</Text>
            {doc ? (
              <Space orientation="vertical" size={8} style={{ width: '100%', marginTop: 10 }}>
                <Text type="secondary">来源：{doc.source_type}</Text>
                {doc.source_url ? (
                  <Text type="secondary" ellipsis>
                    URL：{doc.source_url}
                  </Text>
                ) : null}
                <Text type="secondary">字数：{doc.word_count}</Text>
                <Text strong style={{ marginTop: 8 }}>
                  版本历史
                </Text>
                {versions.map((v) => (
                  <div
                    key={v.id}
                    style={{
                      padding: 8,
                      borderRadius: 8,
                      border: '1px solid rgba(0,0,0,0.06)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 8,
                    }}
                  >
                    <div>
                      <Text>v{v.version}</Text>
                      <div>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {v.change_note || '—'}
                        </Text>
                      </div>
                    </div>
                    <Button
                      size="small"
                      onClick={() => {
                        modal.confirm({
                          title: `回滚到 v${v.version}?`,
                          onOk: async () => {
                            const updated = await rollbackWikiDocument(doc.id, v.version);
                            setDoc(updated);
                            setDraftMd(updated.content_md);
                            setVersions(await listWikiVersions(doc.id));
                            message.success('已回滚');
                          },
                        });
                      }}
                    >
                      回滚
                    </Button>
                  </div>
                ))}
              </Space>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 40 }} />
            )}
          </div>
        ) : null}
      </div>

      <PasteImportModal
        open={pasteOpen}
        spaces={spaces}
        defaultSpaceId={spaceId}
        onClose={() => setPasteOpen(false)}
        onSaved={(id) => {
          void loadDocs();
          void openDoc(id);
        }}
      />
      <UrlClipModal
        open={urlOpen}
        spaces={spaces}
        defaultSpaceId={spaceId}
        onClose={() => setUrlOpen(false)}
        onSaved={(id) => {
          void loadDocs();
          void openDoc(id);
        }}
      />
    </div>
  );
}

function SelectSpaces({
  spaces,
  spaceId,
  onChange,
}: {
  spaces: WikiSpace[];
  spaceId?: number;
  onChange: (id: number) => void;
}) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {spaces.map((s) => (
        <Tag
          key={s.id}
          color={s.id === spaceId ? 'blue' : undefined}
          style={{ cursor: 'pointer' }}
          onClick={() => onChange(s.id)}
        >
          {s.name}
        </Tag>
      ))}
    </div>
  );
}
