/**
 * Skill 设计器 — frontmatter + 正文 + 多文件树.
 *
 * 两个必须传达给用户的 OpenCode 约束：
 * 1. frontmatter **只认 5 个字段**（name/description/license/compatibility/metadata），
 *    多写的会被静默忽略 → 这里只暴露这 5 个，并明确说明
 * 2. 目录名必须等于 name，否则 OpenCode 不加载 → name 不可改
 *
 * 主流优秀实践「渐进披露」：SKILL.md 常驻上下文只放高频规则，
 * 低频细节下沉到 references/*.md 由正文里的链接指引。
 * 所以多文件树是一等公民，正文过长时会主动建议下沉。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App,
  Alert,
  Button,
  Divider,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Segmented,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  DeleteOutlined,
  FileAddOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { extractErrMsg } from '../../stores/computeStore';
import * as svc from '../../services/agentFactory.service';
import type {
  PreviewResponse,
  SkillFileItem,
  SkillTemplate,
  ValidationResult,
} from '../../types/agentFactory';
import { ArtifactPreview, ArtifactTree, ValidationPanel } from './shared';

const { Text } = Typography;

interface FormState {
  name: string;
  display_name: string;
  description: string;
  license: string;
  compatibility: string;
  metadata: Array<{ key: string; value: string }>;
  body: string;
  category: string;
  files: SkillFileItem[];
}

const EMPTY: FormState = {
  name: '',
  display_name: '',
  description: '',
  license: 'MIT',
  compatibility: 'opencode',
  metadata: [],
  body: '',
  category: '',
  files: [],
};

const BODY_TEMPLATE = `# 技能名

## 我做什么
- 一句话说清能力边界

## 何时用我
描述触发场景。若信息不足，先问清再动手。

## 快速流程
1. ...
2. ...

> 低频细节下沉到 [references/detail.md](references/detail.md)，保持本文精简。
`;

function fromTemplate(t: SkillTemplate): FormState {
  return {
    name: t.name,
    display_name: t.display_name ?? '',
    description: t.description,
    license: t.license ?? '',
    compatibility: t.compatibility ?? '',
    metadata: Object.entries(t.metadata_json ?? {}).map(([key, value]) => ({
      key,
      value: String(value),
    })),
    body: t.body ?? '',
    category: t.category ?? '',
    files: t.files ?? [],
  };
}

function toPayload(f: FormState) {
  const md: Record<string, string> = {};
  f.metadata.forEach((m) => {
    if (m.key.trim()) md[m.key.trim()] = m.value;
  });
  return {
    name: f.name.trim(),
    display_name: f.display_name.trim() || undefined,
    description: f.description.trim(),
    license: f.license.trim() || undefined,
    compatibility: f.compatibility.trim() || undefined,
    metadata_json: Object.keys(md).length ? md : undefined,
    body: f.body || undefined,
    category: f.category.trim() || undefined,
    files: f.files.filter((x) => x.rel_path.trim()),
  };
}

export default function SkillDesigner() {
  const { notification } = App.useApp();

  const [list, setList] = useState<SkillTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [keyword, setKeyword] = useState('');

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewPath, setPreviewPath] = useState<string>('');
  const [validation, setValidation] = useState<ValidationResult | null>(null);

  // 编辑哪个附属文件（'' = 编辑 SKILL.md 正文）
  const [editingFile, setEditingFile] = useState<string>('');
  const [newFileOpen, setNewFileOpen] = useState(false);
  const [newFilePath, setNewFilePath] = useState('references/detail.md');
  const [newFileExec, setNewFileExec] = useState(false);

  const selected = useMemo(
    () => list.find((x) => x.id === selectedId) ?? null,
    [list, selectedId],
  );

  const load = useCallback(
    async (kw?: string) => {
      setLoading(true);
      try {
        setList(await svc.listSkills(kw ? { keyword: kw } : undefined));
      } catch (err) {
        notification.error({ title: '获取 Skill 列表失败', description: extractErrMsg(err) });
      } finally {
        setLoading(false);
      }
    },
    [notification],
  );

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selected) {
      setForm(fromTemplate(selected));
      setCreating(false);
      setEditingFile('');
    }
  }, [selected]);

  const refreshPreview = useCallback(async () => {
    if (!selectedId) {
      setPreview(null);
      return;
    }
    try {
      const p = await svc.previewSkill(selectedId);
      setPreview(p);
      setValidation(p.validation);
      setPreviewPath((cur) => cur || p.artifacts[0]?.path || '');
    } catch {
      setPreview(null);
    }
  }, [selectedId]);

  useEffect(() => {
    void refreshPreview();
  }, [refreshPreview]);

  const patch = (p: Partial<FormState>) => setForm((s) => ({ ...s, ...p }));

  const startCreate = () => {
    setSelectedId(null);
    setCreating(true);
    setForm({ ...EMPTY, body: BODY_TEMPLATE });
    setPreview(null);
    setValidation(null);
    setEditingFile('');
  };

  const save = async () => {
    if (!form.name.trim()) {
      notification.warning({ title: '请填写 skill 名', description: '例如 git-release' });
      return;
    }
    if (!form.description.trim()) {
      notification.warning({
        title: '请填写描述',
        description: '这是模型判断「何时加载该 skill」的唯一依据',
      });
      return;
    }
    setSaving(true);
    try {
      if (creating) {
        const created = await svc.createSkill(toPayload(form) as never);
        notification.success({ title: `Skill「${created.name}」已创建` });
        await load(keyword);
        setSelectedId(created.id);
        setCreating(false);
      } else if (selectedId) {
        const { name, ...rest } = toPayload(form);
        void name;
        await svc.updateSkill(selectedId, rest as never);
        notification.success({ title: '已保存' });
        await load(keyword);
        await refreshPreview();
      }
    } catch (err) {
      notification.error({ title: '保存失败', description: extractErrMsg(err), duration: 12 });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (t: SkillTemplate) => {
    try {
      await svc.deleteSkill(t.id);
      notification.success({ title: `已删除 ${t.name}` });
      if (selectedId === t.id) setSelectedId(null);
      await load(keyword);
    } catch (err) {
      notification.error({ title: '删除失败', description: extractErrMsg(err), duration: 10 });
    }
  };

  const addFile = () => {
    const p = newFilePath.trim();
    if (!p) return;
    if (form.files.some((f) => f.rel_path === p)) {
      notification.warning({ title: '路径已存在' });
      return;
    }
    patch({
      files: [...form.files, { rel_path: p, content: '', is_executable: newFileExec }],
    });
    setEditingFile(p);
    setNewFileOpen(false);
    setNewFilePath('references/detail.md');
    setNewFileExec(false);
  };

  const updateFileContent = (path: string, content: string) => {
    patch({
      files: form.files.map((f) => (f.rel_path === path ? { ...f, content } : f)),
    });
  };

  const deleteFile = (path: string) => {
    patch({ files: form.files.filter((f) => f.rel_path !== path) });
    if (editingFile === path) setEditingFile('');
  };

  const columns: ColumnsType<SkillTemplate> = [
    {
      title: 'Skill',
      key: 'name',
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Space size={5}>
            <Text strong style={{ fontSize: 12.5 }}>
              {r.name}
            </Text>
            {r.is_builtin_preset && (
              <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>
                预设
              </Tag>
            )}
            {r.files.length > 0 && (
              <Tooltip title={r.files.map((f) => f.rel_path).join('\n')}>
                <Tag style={{ fontSize: 10, margin: 0 }}>+{r.files.length} 文件</Tag>
              </Tooltip>
            )}
          </Space>
          <Text type="secondary" style={{ fontSize: 10.5 }}>
            {r.category || '未分类'}
          </Text>
        </Space>
      ),
    },
    {
      title: '',
      key: 'act',
      width: 40,
      render: (_, r) =>
        r.is_builtin_preset ? null : (
          <Popconfirm title={`删除 ${r.name}？`} onConfirm={() => remove(r)}>
            <Button
              size="small"
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Popconfirm>
        ),
    },
  ];

  const editing = creating || !!selected;
  const curFile = form.files.find((f) => f.rel_path === editingFile);
  const bodyLines = form.body.split('\n').length;
  const suggestSplit = bodyLines > 400 && form.files.length === 0;

  return (
    <div style={{ display: 'flex', gap: 12, height: '100%', alignItems: 'flex-start' }}>
      {/* 左：列表 */}
      <div style={{ width: 240, flexShrink: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: '14px 12px', display: 'flex', flexDirection: 'column', maxHeight: '100%' }}>
        <Input.Search
          size="small"
          placeholder="搜索 name / 描述"
          allowClear
          style={{ marginBottom: 10 }}
          onSearch={(v) => {
            setKeyword(v);
            void load(v);
          }}
        />
        <Space style={{ marginBottom: 8 }} size={4}>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={startCreate}>
            新建
          </Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={() => void load(keyword)}
          />
        </Space>
        <Table<SkillTemplate>
          size="small"
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={loading}
          pagination={false}
          showHeader={false}
          scroll={{ y: 'calc(100vh - 300px)' }}
          onRow={(r) => ({
            onClick: () => setSelectedId(r.id),
            style: {
              cursor: 'pointer',
              background: selectedId === r.id ? 'rgba(0,113,227,0.06)' : undefined,
            },
          })}
        />
      </div>

      {/* 中：表单 */}
      <div style={{ flex: 1, minWidth: 0, maxHeight: '100%', overflowY: 'auto', padding: 16, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
        {!editing ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                左侧选择一个 Skill 查看/编辑
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  或点「新建」创建（支持 references/ 多文件的渐进披露结构）
                </Text>
              </span>
            }
          />
        ) : (
          <>
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 12 }}
              title="OpenCode 的 frontmatter 只认 5 个字段"
              description={
                <span style={{ fontSize: 12 }}>
                  <Text code>name</Text> <Text code>description</Text>{' '}
                  <Text code>license</Text> <Text code>compatibility</Text>{' '}
                  <Text code>metadata</Text> —— 其余字段会被<b>静默忽略</b>。
                  目录名必须等于 name，否则不会被加载。
                </span>
              }
            />

            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 13 }}>
                Skill 名 <Text type="danger">*</Text>
              </Text>
              <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
                例：git-release（= 落盘目录名 skills/git-release/）
              </Text>
              <Input
                size="small"
                style={{ marginTop: 4, fontFamily: 'monospace' }}
                placeholder="git-release"
                value={form.name}
                disabled={!creating}
                onChange={(e) => patch({ name: e.target.value })}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 13 }}>
                描述 <Text type="danger">*</Text>
              </Text>
              <Tooltip title="模型据此判断何时加载该 skill；写清「我做什么 + 什么场景触发我」">
                <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8 }}>
                  模型选择的唯一依据，≤1024 字符（当前 {form.description.length}）
                </Text>
              </Tooltip>
              <Input.TextArea
                rows={2}
                style={{ marginTop: 4 }}
                placeholder="生成一致的版本发布与变更日志。当准备打 tag 发版、需要从合并的 PR 生成 release notes 时使用。"
                value={form.description}
                onChange={(e) => patch({ description: e.target.value })}
              />
            </div>

            <Space size={10} style={{ marginBottom: 12, flexWrap: 'wrap' }}>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  license
                </Text>
                <Input
                  size="small"
                  placeholder="MIT"
                  value={form.license}
                  onChange={(e) => patch({ license: e.target.value })}
                  style={{ width: 110 }}
                />
              </div>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  compatibility
                </Text>
                <Input
                  size="small"
                  placeholder="opencode"
                  value={form.compatibility}
                  onChange={(e) => patch({ compatibility: e.target.value })}
                  style={{ width: 130 }}
                />
              </div>
              <div>
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                  分类
                </Text>
                <Input
                  size="small"
                  placeholder="workflow"
                  value={form.category}
                  onChange={(e) => patch({ category: e.target.value })}
                  style={{ width: 110 }}
                />
              </div>
            </Space>

            {/* metadata */}
            <div style={{ marginBottom: 14 }}>
              <Text strong style={{ fontSize: 13 }}>
                metadata
              </Text>
              <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8 }}>
                只能是字符串→字符串，例：audience = maintainers
              </Text>
              <div style={{ marginTop: 4 }}>
                {form.metadata.map((m, i) => (
                  <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                    <Input
                      size="small"
                      placeholder="audience"
                      value={m.key}
                      onChange={(e) =>
                        patch({
                          metadata: form.metadata.map((x, j) =>
                            j === i ? { ...x, key: e.target.value } : x,
                          ),
                        })
                      }
                      style={{ width: 150, fontFamily: 'monospace' }}
                    />
                    <Input
                      size="small"
                      placeholder="maintainers"
                      value={m.value}
                      onChange={(e) =>
                        patch({
                          metadata: form.metadata.map((x, j) =>
                            j === i ? { ...x, value: e.target.value } : x,
                          ),
                        })
                      }
                      style={{ flex: 1, fontFamily: 'monospace' }}
                    />
                    <Button
                      size="small"
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() =>
                        patch({ metadata: form.metadata.filter((_, j) => j !== i) })
                      }
                    />
                  </div>
                ))}
                <Button
                  size="small"
                  type="dashed"
                  icon={<PlusOutlined />}
                  onClick={() => patch({ metadata: [...form.metadata, { key: '', value: '' }] })}
                >
                  添加 metadata
                </Button>
              </div>
            </div>

            <Divider style={{ margin: '12px 0' }} />

            {/* 文件切换器 */}
            <div style={{ marginBottom: 8 }}>
              <Space size={8} wrap>
                <Text strong style={{ fontSize: 13 }}>
                  内容
                </Text>
                <Segmented
                  size="small"
                  value={editingFile}
                  onChange={(v) => setEditingFile(v as string)}
                  options={[
                    { label: 'SKILL.md', value: '' },
                    ...form.files.map((f) => ({
                      label: f.rel_path.split('/').pop() || f.rel_path,
                      value: f.rel_path,
                    })),
                  ]}
                />
                <Button
                  size="small"
                  type="dashed"
                  icon={<FileAddOutlined />}
                  onClick={() => setNewFileOpen(true)}
                >
                  加文件
                </Button>
                {editingFile && (
                  <Popconfirm
                    title={`删除 ${editingFile}？`}
                    onConfirm={() => deleteFile(editingFile)}
                  >
                    <Button size="small" type="text" danger icon={<DeleteOutlined />}>
                      删除此文件
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            </div>

            {suggestSplit && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 8 }}
                title="建议使用渐进披露"
                description={
                  <span style={{ fontSize: 12 }}>
                    SKILL.md 会<b>常驻上下文</b>，当前约 {bodyLines} 行偏长。
                    建议把低频细节移到 <Text code>references/*.md</Text>，
                    正文里用链接指引 —— 这是主流 skill 的通用做法。
                  </span>
                }
              />
            )}

            {editingFile === '' ? (
              <>
                <Text type="secondary" style={{ fontSize: 11.5 }}>
                  SKILL.md 正文（frontmatter 之后的 Markdown）
                </Text>
                <Input.TextArea
                  rows={14}
                  style={{ marginTop: 4, fontFamily: 'monospace', fontSize: 12 }}
                  placeholder={BODY_TEMPLATE}
                  value={form.body}
                  onChange={(e) => patch({ body: e.target.value })}
                />
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {bodyLines} 行 · {form.body.length} 字符
                </Text>
              </>
            ) : (
              <>
                <Space size={6}>
                  <FileTextOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
                  <Text code style={{ fontSize: 11.5 }}>
                    {editingFile}
                  </Text>
                  {curFile?.is_executable && <Tag style={{ fontSize: 10 }}>可执行</Tag>}
                </Space>
                <Input.TextArea
                  rows={14}
                  style={{ marginTop: 4, fontFamily: 'monospace', fontSize: 12 }}
                  placeholder="# 细节内容…"
                  value={curFile?.content ?? ''}
                  onChange={(e) => updateFileContent(editingFile, e.target.value)}
                />
              </>
            )}

            <Divider style={{ margin: '12px 0' }} />
            <div style={{ marginBottom: 12 }}>
              <ValidationPanel result={validation} />
            </div>

            <Space size={8}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={saving}
                onClick={() => void save()}
              >
                {creating ? '创建' : '保存'}
              </Button>
              {creating && <Button onClick={() => setCreating(false)}>取消</Button>}
            </Space>
          </>
        )}
      </div>

      {/* 右：产物预览 */}
      <div style={{ width: 360, flexShrink: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: 12, maxHeight: '100%', display: 'flex', flexDirection: 'column' }}>
        <Space size={6} style={{ marginBottom: 6 }}>
          <FileTextOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
          <Text strong style={{ fontSize: 13 }}>
            落盘产物预览
          </Text>
          {selectedId && (
            <Button
              size="small"
              type="text"
              icon={<ReloadOutlined />}
              onClick={() => void refreshPreview()}
            />
          )}
        </Space>
        {preview ? (
          <>
            <ArtifactTree
              artifacts={preview.artifacts}
              selected={previewPath}
              onSelect={setPreviewPath}
            />
            <Divider style={{ margin: '8px 0' }} />
            <ArtifactPreview
              artifact={preview.artifacts.find((a) => a.path === previewPath) ?? preview.artifacts[0]}
              maxHeight={280}
            />
          </>
        ) : (
          <Alert
            type="info"
            showIcon
            title={creating ? '创建后可预览' : '选择一个 Skill'}
            description={
              <span style={{ fontSize: 12 }}>
                预览由后端渲染，与实际写入容器的文件<b>完全一致</b>。
              </span>
            }
          />
        )}
      </div>

      {/* 新增文件 Modal */}
      <Modal
        title="新增附属文件"
        open={newFileOpen}
        onOk={addFile}
        onCancel={() => setNewFileOpen(false)}
        okText="添加"
        width={520}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          title="渐进披露的载体"
          description={
            <span style={{ fontSize: 12 }}>
              <Text code>references/*.md</Text> 放低频细节，
              <Text code>scripts/*.py</Text> 放可执行脚本。
              禁止 <Text code>..</Text> 与绝对路径。
            </span>
          }
        />
        <Text strong style={{ fontSize: 13 }}>
          相对路径
        </Text>
        <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
          例：references/detail.md
        </Text>
        <Input
          size="small"
          style={{ marginTop: 4, fontFamily: 'monospace' }}
          placeholder="references/detail.md"
          value={newFilePath}
          onChange={(e) => setNewFilePath(e.target.value)}
        />
        <div style={{ marginTop: 10 }}>
          <Space size={6}>
            <Text strong style={{ fontSize: 13 }}>
              可执行
            </Text>
            <Segmented
              size="small"
              value={newFileExec ? 'yes' : 'no'}
              onChange={(v) => setNewFileExec(v === 'yes')}
              options={[
                { label: '否（文档）', value: 'no' },
                { label: '是（脚本 0o755）', value: 'yes' },
              ]}
            />
          </Space>
        </div>
      </Modal>
    </div>
  );
}
