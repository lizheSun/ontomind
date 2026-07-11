import { create } from 'zustand';
import type { DpDataSource, DpSchemaResponse } from '../types/dataPlatform';
import { dataPlatformService } from '../services/dataPlatform.service';

interface DataPlatformState {
  sources: DpDataSource[];
  currentSourceId: number | null;
  schemaCache: Record<number, DpSchemaResponse>;
  loading: boolean;
  error: string | null;

  fetchSources: () => Promise<void>;
  setCurrentSource: (id: number | null) => void;
  fetchSchema: (id: number, force?: boolean) => Promise<DpSchemaResponse>;
  createSource: (
    payload: Parameters<typeof dataPlatformService.createSource>[0],
  ) => Promise<DpDataSource>;
  deleteSource: (id: number) => Promise<void>;
  reset: () => void;
}

export const useDataPlatformStore = create<DataPlatformState>((set, get) => ({
  sources: [],
  currentSourceId: null,
  schemaCache: {},
  loading: false,
  error: null,

  async fetchSources() {
    set({ loading: true, error: null });
    try {
      const sources = await dataPlatformService.listSources();
      set({ sources, loading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'fetch failed';
      set({ error: msg, loading: false });
    }
  },

  setCurrentSource(id) {
    set({ currentSourceId: id });
  },

  async fetchSchema(id, force = false) {
    const cached = get().schemaCache[id];
    if (cached && !force) return cached;
    const schema = await dataPlatformService.describeSchema(id);
    set({ schemaCache: { ...get().schemaCache, [id]: schema } });
    return schema;
  },

  async createSource(payload) {
    const row = await dataPlatformService.createSource(payload);
    set({ sources: [row, ...get().sources] });
    return row;
  },

  async deleteSource(id) {
    await dataPlatformService.deleteSource(id);
    set({
      sources: get().sources.filter((s) => s.id !== id),
      currentSourceId:
        get().currentSourceId === id ? null : get().currentSourceId,
    });
  },

  reset() {
    set({
      sources: [],
      currentSourceId: null,
      schemaCache: {},
      loading: false,
      error: null,
    });
  },
}));

export default useDataPlatformStore;
