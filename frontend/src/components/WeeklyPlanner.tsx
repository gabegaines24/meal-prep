import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWeek, assignSlot, clearSlot, autogenerate } from "../api/meals";
import { searchRecipes, getFavorites } from "../api/recipes";
import type { Recipe } from "../api/recipes";
import type { Slot } from "../api/meals";
import RecipeCard from "./RecipeCard";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MEALS = ["breakfast", "lunch", "dinner"] as const;
type MealType = (typeof MEALS)[number];

const MACRO_UNITS: Record<string, string> = {
  calories: "kcal",
  protein: "g",
  carbs: "g",
  fat: "g",
};

interface DrawerState {
  day: number;
  mealType: MealType;
}

export default function WeeklyPlanner() {
  const qc = useQueryClient();
  const [weekStart] = useState<string | undefined>(undefined);
  const [drawer, setDrawer] = useState<DrawerState | null>(null);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Recipe[]>([]);
  const [searching, setSearching] = useState(false);
  const [drawerTab, setDrawerTab] = useState<"search" | "favorites">("search");

  const { data, isLoading } = useQuery({
    queryKey: ["week", weekStart],
    queryFn: () => getWeek(weekStart),
  });

  const { data: favorites = [] } = useQuery({
    queryKey: ["favorites"],
    queryFn: getFavorites,
    enabled: !!drawer,
  });

  const assign = useMutation({
    mutationFn: ({ day, mealType, recipeId }: { day: number; mealType: string; recipeId: number }) =>
      assignSlot(day, mealType, recipeId, weekStart),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week"] });
      qc.invalidateQueries({ queryKey: ["grocery-list"] });
      setDrawer(null);
      setSearch("");
      setSearchResults([]);
    },
  });

  const clear = useMutation({
    mutationFn: ({ day, mealType }: { day: number; mealType: string }) =>
      clearSlot(day, mealType, weekStart),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week"] });
      qc.invalidateQueries({ queryKey: ["grocery-list"] });
    },
  });

  const generate = useMutation({
    mutationFn: () => autogenerate(weekStart),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week"] });
      qc.invalidateQueries({ queryKey: ["grocery-list"] });
    },
  });

  async function handleSearch() {
    if (!search.trim()) return;
    setSearching(true);
    try {
      const results = await searchRecipes(search.trim());
      setSearchResults(results);
    } finally {
      setSearching(false);
    }
  }

  function getSlot(day: number, mealType: MealType): Slot | undefined {
    return data?.slots.find((s) => s.day_of_week === day && s.meal_type === mealType);
  }

  if (isLoading) {
    return <div className="text-center py-12 text-gray-400">Loading meal plan…</div>;
  }

  const gaps = data?.macro_gaps ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-700">
          Week of {data?.week_start_date ?? "—"}
        </h2>
        <button
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          {generate.isPending ? "Generating…" : "Auto-Generate Week"}
        </button>
      </div>

      {gaps.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
          <span className="font-medium">Macro gaps this week: </span>
          {gaps.map((g, i) => (
            <span key={g.macro}>
              {i > 0 && " · "}
              {g.gap > 0 ? `${g.gap.toFixed(0)} short` : `${Math.abs(g.gap).toFixed(0)} over`}{" "}
              {g.macro} ({MACRO_UNITS[g.macro] ?? ""})
            </span>
          ))}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-1">
          <thead>
            <tr>
              <th className="w-24 text-xs text-gray-400 font-normal text-left pb-1">Meal</th>
              {DAYS.map((d) => (
                <th key={d} className="text-xs font-semibold text-gray-600 text-center pb-1 w-36">
                  {d}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MEALS.map((meal) => (
              <tr key={meal}>
                <td className="text-xs font-medium text-gray-400 capitalize pr-2 align-top pt-2">
                  {meal}
                </td>
                {DAYS.map((_, dayIdx) => {
                  const slot = getSlot(dayIdx, meal);
                  return (
                    <td key={dayIdx} className="align-top">
                      {slot?.recipe ? (
                        <RecipeCard
                          recipe={{ ...slot.recipe, ingredients: [], favorited: false } as Recipe}
                          compact
                          onRemove={() => clear.mutate({ day: dayIdx, mealType: meal })}
                        />
                      ) : (
                        <button
                          onClick={() => {
                            setDrawer({ day: dayIdx, mealType: meal });
                            setDrawerTab("search");
                          }}
                          className="w-full h-14 border-2 border-dashed border-gray-200 hover:border-emerald-300 rounded-lg text-gray-300 hover:text-emerald-400 text-xl transition-colors"
                        >
                          +
                        </button>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {drawer && (
        <div className="fixed inset-0 bg-black/40 z-40 flex justify-end" onClick={() => setDrawer(null)}>
          <div
            className="bg-white w-full max-w-sm h-full shadow-xl flex flex-col p-4 gap-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">
                {DAYS[drawer.day]} — {drawer.mealType}
              </h3>
              <button onClick={() => setDrawer(null)} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">×</button>
            </div>

            <div className="flex gap-2 border-b border-gray-100 pb-2">
              {(["search", "favorites"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setDrawerTab(tab)}
                  className={`text-sm px-3 py-1 rounded-lg capitalize ${
                    drawerTab === tab
                      ? "bg-emerald-500 text-white"
                      : "text-gray-500 hover:bg-gray-100"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {drawerTab === "search" ? (
              <>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    placeholder="Search recipes…"
                    className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                  />
                  <button
                    onClick={handleSearch}
                    disabled={searching}
                    className="bg-emerald-500 hover:bg-emerald-600 text-white px-3 py-2 rounded-lg text-sm disabled:opacity-50"
                  >
                    {searching ? "…" : "Go"}
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2">
                  {searchResults.map((r) => (
                    <RecipeCard
                      key={r.id}
                      recipe={r}
                      onSelect={(recipe) =>
                        assign.mutate({ day: drawer.day, mealType: drawer.mealType, recipeId: recipe.id })
                      }
                    />
                  ))}
                  {searchResults.length === 0 && !searching && (
                    <p className="text-sm text-gray-400 text-center pt-8">Search to find recipes</p>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-2">
                {favorites.map((r) => (
                  <RecipeCard
                    key={r.id}
                    recipe={r}
                    onSelect={(recipe) =>
                      assign.mutate({ day: drawer.day, mealType: drawer.mealType, recipeId: recipe.id })
                    }
                  />
                ))}
                {favorites.length === 0 && (
                  <p className="text-sm text-gray-400 text-center pt-8">
                    Star recipes to add them here. Favorites are preferred when auto-generating.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
