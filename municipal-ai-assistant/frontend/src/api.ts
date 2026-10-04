import axios from 'axios';

const BASE = '/api';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Citation {
  source_file: string;
  page: string;
  excerpt: string;
  relevance_score: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  is_uncertain: boolean;
  clarification_request: string | null;
}

export interface DocumentInfo {
  filename: string;
  doc_type: 'knowledge_base' | 'additional_documents';
  chunks: number;
}

export interface TemplateField {
  field_id: string;
  label: string;
  location: string;
  current_value: string | null;
  filled_value: string | null;
  citation: string | null;
  confidence: number;
  status: 'filled' | 'uncertain' | 'needs_user_input';
}

export interface TemplateAnalysis {
  session_id: string;
  filename: string;
  fields: TemplateField[];
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function sendChat(question: string, useAgent = true): Promise<ChatResponse> {
  const res = await axios.post<ChatResponse>(`${BASE}/chat`, {
    question,
    use_agent: useAgent,
  });
  return res.data;
}

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const res = await axios.get<DocumentInfo[]>(`${BASE}/documents`);
  return res.data;
}

export async function uploadDocument(file: File, docType: string): Promise<unknown> {
  const form = new FormData();
  form.append('file', file);
  form.append('doc_type', docType);
  const res = await axios.post(`${BASE}/documents/upload`, form);
  return res.data;
}

export async function deleteDocument(docType: string, filename: string): Promise<unknown> {
  const res = await axios.delete(`${BASE}/documents/${docType}/${encodeURIComponent(filename)}`);
  return res.data;
}

export async function reindexDocuments(): Promise<unknown> {
  const res = await axios.post(`${BASE}/documents/reindex`);
  return res.data;
}

export async function analyzeTemplate(file: File): Promise<TemplateAnalysis> {
  const form = new FormData();
  form.append('file', file);
  const res = await axios.post<TemplateAnalysis>(`${BASE}/templates/analyze`, form);
  return res.data;
}

export async function updateTemplateFields(
  sessionId: string,
  updates: Record<string, string>,
): Promise<{ session_id: string; fields: TemplateField[] }> {
  const res = await axios.post(`${BASE}/templates/update-fields`, {
    session_id: sessionId,
    updates,
  });
  return res.data;
}

export async function exportTemplate(sessionId: string): Promise<Blob> {
  const res = await axios.post(`${BASE}/templates/export/${sessionId}`, null, {
    responseType: 'blob',
  });
  return res.data;
}
