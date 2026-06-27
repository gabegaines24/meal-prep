import type { Recipe } from "../api/recipes";
import { toggleFavorite } from "../api/recipes";
import { useQueryClient } from "@tanstack/react-query";

function CostBadge({ cost }: { cost?: number | null }) {
  if (cost == null) return null;
  return (
    <span className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full px-2 py-0.5">
      ${cost.toFixed(2)}
    </span>
  );
}

interface Props {
  recipe: Recipe;
  compact?: boolean;
  onSelect?: (recipe: Recipe) => void;
  onRemove?: () => void;
}

export default function RecipeCard({ recipe, compact = false, onSelect, onRemove }: Props) {
  const qc = useQueryClient();

  async function handleFavorite(e: React.MouseEvent) {
    e.stopPropagation();
    await toggleFavorite(recipe.id);
    qc.invalidateQueries({ queryKey: ["recipes"] });
  }

  if (compact) {
    return (
      <div
        className="flex items-center justify-between bg-white rounded-lg border border-gray-200 px-3 py-2 gap-2 cursor-pointer hover:border-emerald-400 transition-colors"
        onClick={() => onSelect?.(recipe)}
      >
        <div className="flex items-center gap-2 min-w-0">
          {recipe.image_url && (
            <img
              src={recipe.image_url}
              alt={recipe.title}
              className="w-10 h-10 rounded object-cover shrink-0"
            />
          )}
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{recipe.title}</p>
            {recipe.calories != null && (
              <p className="text-xs text-gray-400">{recipe.calories.toFixed(0)} kcal</p>
            )}
          </div>
        </div>
        {onRemove && (
          <button
            onClick={(e) => { e.stopPropagation(); onRemove(); }}
            className="text-gray-300 hover:text-red-400 text-lg leading-none"
            title="Remove"
          >
            ×
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onSelect?.(recipe)}
    >
      {recipe.image_url && (
        <img
          src={recipe.image_url}
          alt={recipe.title}
          className="w-full h-36 object-cover"
        />
      )}
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-sm leading-tight">{recipe.title}</p>
          <button
            onClick={handleFavorite}
            className={`text-xl shrink-0 ${recipe.favorited ? "text-yellow-400" : "text-gray-300 hover:text-yellow-300"}`}
            title={recipe.favorited ? "Unfavorite" : "Favorite"}
          >
            ★
          </button>
        </div>
        {recipe.estimated_cost != null && (
          <div className="mt-1">
            <CostBadge cost={recipe.estimated_cost} />
          </div>
        )}
        <div className="mt-2 grid grid-cols-4 gap-1 text-center text-xs">
          {[
            { label: "Cal", value: recipe.calories },
            { label: "Pro", value: recipe.protein, unit: "g" },
            { label: "Carb", value: recipe.carbs, unit: "g" },
            { label: "Fat", value: recipe.fat, unit: "g" },
          ].map(({ label, value, unit = "" }) => (
            <div key={label} className="bg-gray-50 rounded p-1">
              <div className="font-bold text-emerald-600">
                {value != null ? `${value.toFixed(0)}${unit}` : "—"}
              </div>
              <div className="text-gray-400">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
