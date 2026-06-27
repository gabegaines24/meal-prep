function _triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadGroceryList(weekStart?: string): Promise<void> {
  const url = weekStart
    ? `/api/files/grocery-list?week_start=${weekStart}`
    : "/api/files/grocery-list";
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const date = weekStart ?? new Date().toISOString().slice(0, 10);
  _triggerDownload(blob, `grocery-list-${date}.html`);
}

export async function downloadRecipeBook(weekStart?: string): Promise<void> {
  const url = weekStart
    ? `/api/files/recipe-book?week_start=${weekStart}`
    : "/api/files/recipe-book";
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const date = weekStart ?? new Date().toISOString().slice(0, 10);
  _triggerDownload(blob, `recipe-book-${date}.html`);
}
