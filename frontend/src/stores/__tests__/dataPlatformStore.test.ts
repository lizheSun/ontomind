import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useDataPlatformStore } from '../dataPlatformStore';
import { dataPlatformService } from '../../services/dataPlatform.service';

vi.mock('../../services/dataPlatform.service', () => ({
  dataPlatformService: {
    listSources: vi.fn(),
    describeSchema: vi.fn(),
    createSource: vi.fn(),
    deleteSource: vi.fn(),
    getSource: vi.fn(),
  },
}));

describe('useDataPlatformStore', () => {
  beforeEach(() => {
    useDataPlatformStore.getState().reset();
    vi.clearAllMocks();
  });

  it('fetchSources updates sources array and clears loading', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (dataPlatformService.listSources as any).mockResolvedValue([
      { id: 1, name: 'a' },
    ]);
    await useDataPlatformStore.getState().fetchSources();
    const state = useDataPlatformStore.getState();
    expect(state.sources).toHaveLength(1);
    expect(state.loading).toBe(false);
    expect(state.error).toBe(null);
  });

  it('fetchSchema caches result per source_id', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (dataPlatformService.describeSchema as any).mockResolvedValue({
      databases: [],
    });
    await useDataPlatformStore.getState().fetchSchema(1);
    await useDataPlatformStore.getState().fetchSchema(1);
    expect(dataPlatformService.describeSchema).toHaveBeenCalledTimes(1);
    expect(useDataPlatformStore.getState().schemaCache[1]).toBeDefined();
  });

  it('deleteSource removes source and clears currentSourceId when matched', async () => {
    useDataPlatformStore.setState({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      sources: [{ id: 1, name: 'x' } as any, { id: 2, name: 'y' } as any],
      currentSourceId: 1,
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (dataPlatformService.deleteSource as any).mockResolvedValue(undefined);
    await useDataPlatformStore.getState().deleteSource(1);
    const state = useDataPlatformStore.getState();
    expect(state.sources).toHaveLength(1);
    expect(state.sources[0].id).toBe(2);
    expect(state.currentSourceId).toBe(null);
  });
});
