export type KbLibraryCode = 'data_asset' | 'code_repo' | 'document' | 'experience';

export interface KbLibrary {
  id: number;
  code: KbLibraryCode;
  nameZh: string;
  icon: string;
  description: string | null;
  sortOrder: number;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface KbDataAsset {
  id: number;
  libraryId: number;
  titleZh: string;
  titleEn: string | null;
  domain: string | null;
  ownerUserId: number;
  descriptionMd: string | null;
  refMetaTableId: number | null;
  refDataSourceId: number | null;
  tags: string[] | null;
  createdByUserId: number;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface KbDataAssetCreate {
  library_id: number;
  title_zh: string;
  title_en?: string | null;
  domain?: string | null;
  owner_user_id?: number | null;
  description_md?: string | null;
  ref_meta_table_id?: number | null;
  ref_data_source_id?: number | null;
  tags?: string[] | null;
}

export interface KbDataAssetUpdate {
  title_zh?: string;
  title_en?: string | null;
  domain?: string | null;
  owner_user_id?: number | null;
  description_md?: string | null;
  ref_meta_table_id?: number | null;
  ref_data_source_id?: number | null;
  tags?: string[] | null;
}

export interface KbCodeRepo {
  id: number;
  libraryId: number;
  titleZh: string;
  repoUrl: string;
  branch: string;
  language: string | null;
  descriptionMd: string | null;
  tags: string[] | null;
  ownerUserId: number;
  createdByUserId: number;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface KbCodeRepoCreate {
  library_id: number;
  title_zh: string;
  repo_url: string;
  branch?: string;
  language?: string | null;
  description_md?: string | null;
  tags?: string[] | null;
  owner_user_id?: number | null;
}

export interface KbCodeRepoUpdate {
  title_zh?: string;
  repo_url?: string;
  branch?: string;
  language?: string | null;
  description_md?: string | null;
  tags?: string[] | null;
  owner_user_id?: number | null;
}

export interface KbDocument {
  id: number;
  libraryId: number;
  titleZh: string;
  filename: string;
  storagePath: string;
  mimeType: string;
  sizeBytes: number;
  descriptionMd: string | null;
  tags: string[] | null;
  ownerUserId: number;
  createdByUserId: number;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface KbDocumentUpdate {
  title_zh?: string;
  description_md?: string | null;
  tags?: string[] | null;
  owner_user_id?: number | null;
}

export interface KbExperience {
  id: number;
  libraryId: number;
  titleZh: string;
  scenario: string | null;
  contentMd: string;
  outcome: string | null;
  tags: string[] | null;
  ownerUserId: number;
  createdByUserId: number;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface KbExperienceCreate {
  library_id: number;
  title_zh: string;
  scenario?: string | null;
  content_md: string;
  outcome?: string | null;
  tags?: string[] | null;
  owner_user_id?: number | null;
}

export interface KbExperienceUpdate {
  title_zh?: string;
  scenario?: string | null;
  content_md?: string;
  outcome?: string | null;
  tags?: string[] | null;
  owner_user_id?: number | null;
}

export interface KbTag {
  id: number;
  name: string;
  color: string;
}

export interface KbSearchResult {
  libraryCode: KbLibraryCode;
  id: number;
  title: string;
  snippet: string | null;
  score: number;
}

export interface KbSearchGrouped {
  dataAsset: KbSearchResult[];
  codeRepo: KbSearchResult[];
  document: KbSearchResult[];
  experience: KbSearchResult[];
}
