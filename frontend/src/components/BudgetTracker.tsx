import { useQuery } from "@tanstack/react-query";
import { getWeek } from "../api/meals";
import { getProfile } from "../api/profile";

export default function BudgetTracker() {
  const { data: week } = useQuery({ queryKey: ["week"], queryFn: () => getWeek() });
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  if (!profile || !profile.weekly_budget || profile.weekly_budget <= 0) return null;

  // Sum estimated_cost across all unique recipes in the week
  const seenIds = new Set<number>();
  let totalCost = 0;
  for (const slot of week?.slots ?? []) {
    const r = slot.recipe as (typeof slot.recipe & { estimated_cost?: number }) | undefined;
    if (r && !seenIds.has(r.id)) {
      seenIds.add(r.id);
      if ((r as any).estimated_cost != null) totalCost += (r as any).estimated_cost;
    }
  }

  const budget = profile.weekly_budget;
  const pct = budget > 0 ? Math.min((totalCost / budget) * 100, 100) : 0;
  const over = totalCost > budget;
  const hasData = totalCost > 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-gray-700">
          Weekly Budget
          {profile.store_name && (
            <span className="text-gray-400 font-normal ml-1">· {profile.store_name}</span>
          )}
        </span>
        <span className={`text-sm font-bold ${over ? "text-red-500" : "text-emerald-600"}`}>
          {hasData ? (
            <>
              ${totalCost.toFixed(2)}{" "}
              <span className="text-gray-400 font-normal">/ ${budget.toFixed(2)}</span>
            </>
          ) : (
            <span className="text-gray-400 font-normal">
              Budget: ${budget.toFixed(2)} · Add Kroger keys for prices
            </span>
          )}
        </span>
      </div>
      {hasData && (
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${over ? "bg-red-500" : "bg-emerald-400"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
