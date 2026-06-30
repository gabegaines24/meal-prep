const BASE = "/api/ingest";

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  chunks: number;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/document`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${BASE}/documents/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

export async function backfillRecipes(): Promise<{ embedded: number; total: number }> {
  const res = await fetch(`${BASE}/backfill`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
