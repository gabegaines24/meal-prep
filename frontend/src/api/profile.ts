const BASE = "/api/profile";

export interface Profile {
  allergens: string[];
  diet_type: string;
}

export async function getProfile(): Promise<Profile> {
  const res = await fetch(BASE);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateProfile(profile: Profile): Promise<Profile> {
  const res = await fetch(BASE, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
