import { create } from 'zustand';
import type {
  KbLibrary,
  KbLibraryCode,
  KbSearchGrouped,
} from '../types/knowledgeBase';
import { knowledgeBaseService } from '../services/knowledgeBase.service';

interface KnowledgeBaseState {
  libraries: KbLibrary[];
  currentLibraryCode: KbLibraryCode | null;
  searchQuery: string;
  searchGrouped: KbSearchGrouped | null;
  loading: boolean;
  error: string | null;

  fetchLibraries: () => Promise<void>;
  setCurrentLibrary: (code: KbLibraryCode | null) => void;
  search: (q: string, libraryCode?: KbLibraryCode) => Promise<void>;
  clearSearch: () => void;
  reset: () => void;
}

export const useKnowledgeBaseStore = create<KnowledgeBaseState>((set) => ({
  libraries: [],
  currentLibraryCode: null,
  searchQuery: '',
  searchGrouped: null,
  loading: false,
  error: null,

  async fetchLibraries() {
    set({ loading: true, error: null });
    try {
      const libraries = await knowledgeBaseService.listLibraries();
      set({ libraries, loading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'fetch failed';
      set({ error: msg, loading: false });
    }
  },

  setCurrentLibrary(code) {
    set({ currentLibraryCode: code });
  },

  async search(q, libraryCode) {
    set({ loading: true, error: null, searchQuery: q });
    try {
      const grouped = await knowledgeBaseService.search(q, libraryCode);
      set({ searchGrouped: grouped, loading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'search failed';
      set({ error: msg, loading: false });
    }
  },

  clearSearch() {
    set({ searchQuery: '', searchGrouped: null });
  },

  reset() {
    set({
      libraries: [],
      currentLibraryCode: null,
      searchQuery: '',
      searchGrouped: null,
      loading: false,
      error: null,
    });
  },
}));

export default useKnowledgeBaseStore;
