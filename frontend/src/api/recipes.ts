const BASE = "/api/recipes";

export interface Recipe {
  id: number;
  spoonacular_id?: number;
  title: string;
  image_url?: string;
  source_url?: string;
  calories?: number;
  protein?: number;
  carbs?: number;
  fat?: number;
  ingredients: string[];
  estimated_cost_per_serving?: number | null;
  price_source?: string | null;
  favorited: boolean;
}

export async function searchRecipes(query: string): Promise<Recipe[]> {
  const res = await fetch(`${BASE}/search?query=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getRecipe(id: number): Promise<Recipe> {
  const res = await fetch(`${BASE}/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getFavorites(): Promise<Recipe[]> {
  const res = await fetch(`${BASE}/favorites`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function toggleFavorite(id: number): Promise<Recipe> {
  const res = await fetch(`${BASE}/${id}/favorite`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
