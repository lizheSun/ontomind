import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useKnowledgeBaseStore } from '../knowledgeBaseStore';
import { knowledgeBaseService } from '../../services/knowledgeBase.service';

vi.mock('../../services/knowledgeBase.service', () => ({
  knowledgeBaseService: {
    listLibraries: vi.fn(),
    search: vi.fn(),
  },
}));

describe('useKnowledgeBaseStore', () => {
  beforeEach(() => {
    useKnowledgeBaseStore.getState().reset();
    vi.clearAllMocks();
  });

  it('fetchLibraries populates libraries array', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (knowledgeBaseService.listLibraries as any).mockResolvedValue([
      { id: 1, code: 'data_asset', nameZh: '数据资产' },
    ]);
    await useKnowledgeBaseStore.getState().fetchLibraries();
    const state = useKnowledgeBaseStore.getState();
    expect(state.libraries).toHaveLength(1);
    expect(state.libraries[0].code).toBe('data_asset');
    expect(state.loading).toBe(false);
  });

  it('search stores query and grouped result', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (knowledgeBaseService.search as any).mockResolvedValue({
      dataAsset: [
        { libraryCode: 'data_asset', id: 1, title: 'x', snippet: null, score: 1 },
      ],
      codeRepo: [],
      document: [],
      experience: [],
    });
    await useKnowledgeBaseStore.getState().search('foo');
    const state = useKnowledgeBaseStore.getState();
    expect(state.searchQuery).toBe('foo');
    expect(state.searchGrouped?.dataAsset).toHaveLength(1);
    expect(state.searchGrouped?.codeRepo).toEqual([]);
  });
});
