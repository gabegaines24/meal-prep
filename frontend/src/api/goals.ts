const BASE = "/api/goals";

export interface Goals {
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
}

export async function getGoals(): Promise<Goals> {
  const res = await fetch(BASE);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateGoals(goals: Goals): Promise<Goals> {
  const res = await fetch(BASE, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(goals),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
