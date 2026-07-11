import api from './api';
import type {
  KbLibrary,
  KbLibraryCode,
  KbDataAsset,
  KbDataAssetCreate,
  KbDataAssetUpdate,
  KbCodeRepo,
  KbCodeRepoCreate,
  KbCodeRepoUpdate,
  KbDocument,
  KbDocumentUpdate,
  KbExperience,
  KbExperienceCreate,
  KbExperienceUpdate,
  KbTag,
  KbSearchResult,
  KbSearchGrouped,
} from '../types/knowledgeBase';

interface Envelope<T> {
  code: string;
  message: string;
  data: T;
  total?: number;
}

function unwrap<T>(res: { data: Envelope<T> }): T {
  if (res.data?.code !== 'SUCCESS') {
    throw new Error(res.data?.message ?? 'API error');
  }
  return res.data.data;
}

// -- mappers ---------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapLibrary(raw: any): KbLibrary {
  return {
    id: raw.id,
    code: raw.code,
    nameZh: raw.name_zh,
    icon: raw.icon,
    description: raw.description,
    sortOrder: raw.sort_order,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapDataAsset(raw: any): KbDataAsset {
  return {
    id: raw.id,
    libraryId: raw.library_id,
    titleZh: raw.title_zh,
    titleEn: raw.title_en,
    domain: raw.domain,
    ownerUserId: raw.owner_user_id,
    descriptionMd: raw.description_md,
    refMetaTableId: raw.ref_meta_table_id,
    refDataSourceId: raw.ref_data_source_id,
    tags: raw.tags,
    createdByUserId: raw.created_by_user_id,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapCodeRepo(raw: any): KbCodeRepo {
  return {
    id: raw.id,
    libraryId: raw.library_id,
    titleZh: raw.title_zh,
    repoUrl: raw.repo_url,
    branch: raw.branch,
    language: raw.language,
    descriptionMd: raw.description_md,
    tags: raw.tags,
    ownerUserId: raw.owner_user_id,
    createdByUserId: raw.created_by_user_id,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapDocument(raw: any): KbDocument {
  return {
    id: raw.id,
    libraryId: raw.library_id,
    titleZh: raw.title_zh,
    filename: raw.filename,
    storagePath: raw.storage_path,
    mimeType: raw.mime_type,
    sizeBytes: raw.size_bytes,
    descriptionMd: raw.description_md,
    tags: raw.tags,
    ownerUserId: raw.owner_user_id,
    createdByUserId: raw.created_by_user_id,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapExperience(raw: any): KbExperience {
  return {
    id: raw.id,
    libraryId: raw.library_id,
    titleZh: raw.title_zh,
    scenario: raw.scenario,
    contentMd: raw.content_md,
    outcome: raw.outcome,
    tags: raw.tags,
    ownerUserId: raw.owner_user_id,
    createdByUserId: raw.created_by_user_id,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapTag(raw: any): KbTag {
  return { id: raw.id, name: raw.name, color: raw.color };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapSearchResult(raw: any): KbSearchResult {
  return {
    libraryCode: raw.library_code,
    id: raw.id,
    title: raw.title,
    snippet: raw.snippet,
    score: raw.score,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapSearchGrouped(raw: any): KbSearchGrouped {
  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    dataAsset: (raw.data_asset ?? []).map(mapSearchResult),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    codeRepo: (raw.code_repo ?? []).map(mapSearchResult),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    document: (raw.document ?? []).map(mapSearchResult),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    experience: (raw.experience ?? []).map(mapSearchResult),
  };
}

// -- service ---------------------------------------------------

export const knowledgeBaseService = {
  // libraries
  async listLibraries(): Promise<KbLibrary[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/knowledge-base/libraries'));
    return list.map(mapLibrary);
  },

  // data-assets
  async listDataAssets(libraryId?: number): Promise<KbDataAsset[]> {
    const params = libraryId ? { library_id: libraryId } : undefined;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/knowledge-base/data-assets', { params }));
    return list.map(mapDataAsset);
  },
  async getDataAsset(id: number): Promise<KbDataAsset> {
    return mapDataAsset(unwrap(await api.get(`/knowledge-base/data-assets/${id}`)));
  },
  async createDataAsset(payload: KbDataAssetCreate): Promise<KbDataAsset> {
    return mapDataAsset(unwrap(await api.post('/knowledge-base/data-assets', payload)));
  },
  async updateDataAsset(id: number, patch: KbDataAssetUpdate): Promise<KbDataAsset> {
    return mapDataAsset(
      unwrap(await api.put(`/knowledge-base/data-assets/${id}`, patch)),
    );
  },
  async deleteDataAsset(id: number): Promise<void> {
    unwrap(await api.delete(`/knowledge-base/data-assets/${id}`));
  },

  // code-repos
  async listCodeRepos(libraryId?: number): Promise<KbCodeRepo[]> {
    const params = libraryId ? { library_id: libraryId } : undefined;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/knowledge-base/code-repos', { params }));
    return list.map(mapCodeRepo);
  },
  async getCodeRepo(id: number): Promise<KbCodeRepo> {
    return mapCodeRepo(unwrap(await api.get(`/knowledge-base/code-repos/${id}`)));
  },
  async createCodeRepo(payload: KbCodeRepoCreate): Promise<KbCodeRepo> {
    return mapCodeRepo(unwrap(await api.post('/knowledge-base/code-repos', payload)));
  },
  async updateCodeRepo(id: number, patch: KbCodeRepoUpdate): Promise<KbCodeRepo> {
    return mapCodeRepo(unwrap(await api.put(`/knowledge-base/code-repos/${id}`, patch)));
  },
  async deleteCodeRepo(id: number): Promise<void> {
    unwrap(await api.delete(`/knowledge-base/code-repos/${id}`));
  },

  // documents
  async listDocuments(libraryId?: number): Promise<KbDocument[]> {
    const params = libraryId ? { library_id: libraryId } : undefined;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/knowledge-base/documents', { params }));
    return list.map(mapDocument);
  },
  async getDocument(id: number): Promise<KbDocument> {
    return mapDocument(unwrap(await api.get(`/knowledge-base/documents/${id}`)));
  },
  async uploadDocument(
    file: File,
    meta: { titleZh: string; libraryId: number; descriptionMd?: string },
  ): Promise<KbDocument> {
    const form = new FormData();
    form.append('file', file);
    form.append('title_zh', meta.titleZh);
    form.append('library_id', String(meta.libraryId));
    if (meta.descriptionMd !== undefined) {
      form.append('description_md', meta.descriptionMd);
    }
    const res = await api.post('/knowledge-base/documents', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return mapDocument(unwrap(res));
  },
  async downloadDocument(id: number): Promise<Blob> {
    const res = await api.get(`/knowledge-base/documents/${id}/download`, {
      responseType: 'blob',
    });
    return res.data as Blob;
  },
  async updateDocument(id: number, patch: KbDocumentUpdate): Promise<KbDocument> {
    return mapDocument(unwrap(await api.put(`/knowledge-base/documents/${id}`, patch)));
  },
  async deleteDocument(id: number): Promise<void> {
    unwrap(await api.delete(`/knowledge-base/documents/${id}`));
  },

  // experiences
  async listExperiences(libraryId?: number): Promise<KbExperience[]> {
    const params = libraryId ? { library_id: libraryId } : undefined;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/knowledge-base/experiences', { params }));
    return list.map(mapExperience);
  },
  async getExperience(id: number): Promise<KbExperience> {
    return mapExperience(unwrap(await api.get(`/knowledge-base/experiences/${id}`)));
  },
  async createExperience(payload: KbExperienceCreate): Promise<KbExperience> {
    return mapExperience(unwrap(await api.post('/knowledge-base/experiences', payload)));
  },
  async updateExperience(id: number, patch: KbExperienceUpdate): Promise<KbExperience> {
    return mapExperience(
      unwrap(await api.put(`/knowledge-base/experiences/${id}`, patch)),
    );
  },
  async deleteExperience(id: number): Promise<void> {
    unwrap(await api.delete(`/knowledge-base/experiences/${id}`));
  },

  // tags
  async listTags(): Promise<KbTag[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/knowledge-base/tags'));
    return list.map(mapTag);
  },

  // search
  async search(q: string, libraryCode?: KbLibraryCode): Promise<KbSearchGrouped> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const params: any = { q };
    if (libraryCode) params.library_code = libraryCode;
    return mapSearchGrouped(unwrap(await api.get('/knowledge-base/search', { params })));
  },
};

export default knowledgeBaseService;
