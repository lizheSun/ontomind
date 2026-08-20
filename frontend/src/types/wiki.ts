/** Wiki 类型 */
export type WikiSourceType = 'paste' | 'markdown' | 'url' | 'manual';
export type WikiDocStatus = 'draft' | 'published';

export interface WikiSpace {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  sort_order: number;
}

export interface WikiDocumentListItem {
  id: number;
  space_id: number;
  parent_id?: number | null;
  title: string;
  slug: string;
  source_type: WikiSourceType | string;
  source_url?: string | null;
  tags?: string[] | null;
  status: WikiDocStatus | string;
  current_version: number;
  word_count: number;
  author_user_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface WikiDocument extends WikiDocumentListItem {
  content_md: string;
  source_meta?: Record<string, unknown> | null;
}

export interface WikiDocumentVersion {
  id: number;
  document_id: number;
  version: number;
  title: string;
  content_md: string;
  change_note?: string | null;
  author_user_id?: number | null;
  created_at?: string | null;
}

export interface WikiImportPayload {
  source_type: WikiSourceType;
  title?: string;
  content_md: string;
  source_url?: string;
  source_meta?: Record<string, unknown>;
  space_id?: number;
  parent_id?: number;
  tags?: string[];
  status?: WikiDocStatus;
}
