import { describe, it, expect, vi, beforeEach } from 'vitest';
import { dataPlatformService } from '../dataPlatform.service';
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

describe('dataPlatformService mapper', () => {
  beforeEach(() => vi.clearAllMocks());

  it('maps snake_case source to camelCase', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.get as any).mockResolvedValue({
      data: {
        code: 'SUCCESS',
        message: 'ok',
        data: [
          {
            id: 1,
            name: 'src',
            source_type: 'mysql',
            dialect: 'mysql',
            host: 'h',
            port: 3306,
            username: 'u',
            database: 'db',
            default_schema: null,
            charset: 'utf8mb4',
            description: null,
            status: 'active',
            read_only_flag: true,
            has_password: true,
            owner_user_id: 42,
            created_by_user_id: 42,
            extra_params: null,
            created_at: null,
            updated_at: null,
          },
        ],
      },
    });
    const rows = await dataPlatformService.listSources();
    expect(rows[0].sourceType).toBe('mysql');
    expect(rows[0].hasPassword).toBe(true);
    expect(rows[0].ownerUserId).toBe(42);
    expect(rows[0].readOnlyFlag).toBe(true);
  });

  it('throws on non-SUCCESS envelope', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.get as any).mockResolvedValue({
      data: { code: 'ERROR', message: '失败', data: null },
    });
    await expect(dataPlatformService.listSources()).rejects.toThrow('失败');
  });

  it('buildStreamUrl encodes sql query param', () => {
    const url = dataPlatformService.buildStreamUrl(1, 'SELECT * FROM users', 500);
    expect(url).toContain('/data-platform/sources/1/execute/stream');
    expect(url).toContain('sql=SELECT+%2A+FROM+users');
    expect(url).toContain('max_rows=500');
  });
});
