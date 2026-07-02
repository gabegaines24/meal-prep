import { useQuery } from "@tanstack/react-query";
import { fetchBudgetSummary } from "../api/files";

export default function BudgetTracker() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["budget-summary"],
    queryFn: () => fetchBudgetSummary(),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-sm text-gray-400">
        Loading budget…
      </div>
    );
  }

  if (error || !data || !data.budget || data.budget <= 0) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        Set a weekly budget on your{" "}
        <a href="/profile" className="underline font-medium">Profile</a>{" "}
        to filter recipes and track grocery spend.
      </div>
    );
  }

  const pct = data.budget > 0 ? Math.min((data.estimated_total / data.budget) * 100, 100) : 0;
  const over = data.over_budget;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-gray-700">
          Weekly Budget
          {(data.zip_code || data.store_name) && (
            <span className="text-gray-400 font-normal ml-1">
              · {data.zip_code ? `Walmart · ${data.zip_code}` : data.store_name}
            </span>
          )}
        </span>
        <span className={`text-sm font-bold ${over ? "text-red-500" : "text-emerald-600"}`}>
          ${data.estimated_total.toFixed(2)}{" "}
          <span className="text-gray-400 font-normal">/ ${data.budget.toFixed(2)}</span>
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${over ? "bg-red-500" : "bg-emerald-400"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {data.prices_as_of && (
        <p className="text-xs text-gray-400 mt-2">
          Prices as of {data.prices_as_of.slice(0, 10)}
          {data.stale ? " (estimated — verify in store)" : ""}
        </p>
      )}
    </div>
  );
}
