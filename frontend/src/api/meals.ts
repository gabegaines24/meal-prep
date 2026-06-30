const BASE = "/api/meals";

export interface RecipeSummary {
  id: number;
  title: string;
  image_url?: string;
  calories?: number;
  protein?: number;
  carbs?: number;
  fat?: number;
}

export interface Slot {
  id: number;
  week_start_date: string;
  day_of_week: number;
  meal_type: "breakfast" | "lunch" | "dinner";
  recipe?: RecipeSummary;
}

export interface DayMacros {
  day: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
}

export interface WeekResponse {
  week_start_date: string;
  slots: Slot[];
  daily_macros: DayMacros[];
  weekly_macros: { calories: number; protein: number; carbs: number; fat: number };
  macro_gaps?: MacroGap[];
}

export interface MacroGap {
  macro: string;
  actual: number;
  target: number;
  gap: number;
}

export async function getWeek(weekStart?: string): Promise<WeekResponse> {
  const url = weekStart ? `${BASE}?week_start=${weekStart}` : BASE;
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function assignSlot(
  day: number,
  mealType: string,
  recipeId: number,
  weekStart?: string
): Promise<Slot> {
  const url = weekStart
    ? `${BASE}/${day}/${mealType}?week_start=${weekStart}`
    : `${BASE}/${day}/${mealType}`;
  const res = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recipe_id: recipeId }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function clearSlot(
  day: number,
  mealType: string,
  weekStart?: string
): Promise<void> {
  const url = weekStart
    ? `${BASE}/${day}/${mealType}?week_start=${weekStart}`
    : `${BASE}/${day}/${mealType}`;
  await fetch(url, { method: "DELETE" });
}

export async function autogenerate(weekStart?: string): Promise<WeekResponse> {
  const url = weekStart
    ? `${BASE}/autogenerate?week_start=${weekStart}`
    : `${BASE}/autogenerate`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
