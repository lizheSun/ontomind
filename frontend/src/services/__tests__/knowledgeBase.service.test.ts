import { describe, it, expect, vi, beforeEach } from 'vitest';
import { knowledgeBaseService } from '../knowledgeBase.service';
import api from '../api';

vi.mock('../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: 'http://x/api/v1' },
  },
}));

describe('knowledgeBaseService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('maps library camelCase from snake_case', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.get as any).mockResolvedValue({
      data: {
        code: 'SUCCESS',
        message: 'ok',
        data: [
          {
            id: 1,
            code: 'data_asset',
            name_zh: '数据资产',
            icon: 'DatabaseOutlined',
            description: 'desc',
            sort_order: 1,
            created_at: null,
            updated_at: null,
          },
        ],
      },
    });
    const libs = await knowledgeBaseService.listLibraries();
    expect(libs[0].code).toBe('data_asset');
    expect(libs[0].nameZh).toBe('数据资产');
    expect(libs[0].sortOrder).toBe(1);
  });

  it('search returns 4 buckets with camelCase libraryCode', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.get as any).mockResolvedValue({
      data: {
        code: 'SUCCESS',
        message: 'ok',
        data: {
          data_asset: [
            { library_code: 'data_asset', id: 1, title: 'x', snippet: null, score: 1 },
          ],
          code_repo: [],
          document: [],
          experience: [],
        },
      },
    });
    const g = await knowledgeBaseService.search('x');
    expect(g.dataAsset).toHaveLength(1);
    expect(g.dataAsset[0].libraryCode).toBe('data_asset');
    expect(g.codeRepo).toEqual([]);
    expect(g.document).toEqual([]);
    expect(g.experience).toEqual([]);
  });

  it('throws on non-SUCCESS envelope', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.get as any).mockResolvedValue({
      data: { code: 'ERROR', message: '失败', data: null },
    });
    await expect(knowledgeBaseService.listLibraries()).rejects.toThrow('失败');
  });

  it('uploadDocument sends FormData to documents endpoint', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.post as any).mockResolvedValue({
      data: {
        code: 'SUCCESS',
        message: '上传成功',
        data: {
          id: 1,
          library_id: 3,
          title_zh: 'x',
          filename: 'x.md',
          storage_path: 'p',
          mime_type: 'text/markdown',
          size_bytes: 10,
          description_md: null,
          tags: null,
          owner_user_id: 1,
          created_by_user_id: 1,
          created_at: null,
          updated_at: null,
        },
      },
    });
    const file = new File(['# x'], 'x.md', { type: 'text/markdown' });
    const result = await knowledgeBaseService.uploadDocument(file, {
      titleZh: 'x',
      libraryId: 3,
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const call = (api.post as any).mock.calls[0];
    expect(call[0]).toContain('/knowledge-base/documents');
    expect(call[1]).toBeInstanceOf(FormData);
    expect(result.titleZh).toBe('x');
    expect(result.libraryId).toBe(3);
  });
});
