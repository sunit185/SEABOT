export interface SourceChip {
  chunk_id?: string;
  doc_id?: string;
  doc_name?: string;
  page?: number;
  chunk_text?: string;
  bbox?: string;
  thumbnail_path?: string;
}

export interface Message {
  id: string;
  chat_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  is_partial: number;
  interrupted: number;
  created_at: string;
  sources?: SourceChip[];
}

export interface Chat {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatDetail {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface GroupedChats {
  today: Chat[];
  yesterday: Chat[];
  previous_7_days: Chat[];
  older: Chat[];
}

export interface DocumentItem {
  id: string;
  name: string;
  file_type?: string;
  pages?: number;
  status: 'uploading' | 'parsing' | 'indexing' | 'ready' | 'failed';
  error_msg?: string;
  size_bytes?: number;
  created_at: string;
  starter_questions?: string[];
}

export interface UserState {
  id?: number;
  active_chat_id?: string | null;
  sidebar_collapsed: number;
  sidebar_scroll: number;
  viewer_doc_id?: string | null;
  viewer_page?: number | null;
  input_draft?: string | null;
  updated_at?: string;
}

export interface ViewerPageData {
  page_image_base64: string;
  width: number;
  height: number;
  page_num: number;
  total_pages: number;
  chunks: Array<{
    chunk_id: string;
    bbox?: number[];
    text_preview?: string;
  }>;
}

export interface ViewerSheetData {
  sheet_name: string;
  content_markdown: string;
  total_rows: number;
}
