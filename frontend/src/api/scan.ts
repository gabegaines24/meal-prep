import type { Recipe } from "./recipes";

export interface ScanResult {
  ingredients: string[];
  recipes: Recipe[];
  agent_prompt?: string | null;
}

export async function scanFridge(file: File): Promise<ScanResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/scan", { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
