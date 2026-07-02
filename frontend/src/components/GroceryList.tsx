import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchGroceryList } from "../api/files";

function checkedKey(weekStart: string, name: string) {
  return `grocery-checked:${weekStart}:${name}`;
}

function formatPrice(price?: number | null) {
  if (price == null) return null;
  return `$${price.toFixed(2)}`;
}

export default function GroceryList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["grocery-list"],
    queryFn: () => fetchGroceryList(),
  });

  const [checked, setChecked] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!data) return;
    const stored: Record<string, boolean> = {};
    for (const item of data.items) {
      const key = checkedKey(data.week_start_date, item.name);
      stored[item.name] = localStorage.getItem(key) === "1";
    }
    setChecked(stored);
  }, [data]);

  function toggle(name: string) {
    if (!data) return;
    const next = !checked[name];
    setChecked((prev) => ({ ...prev, [name]: next }));
    localStorage.setItem(checkedKey(data.week_start_date, name), next ? "1" : "0");
  }

  if (isLoading) {
    return <div className="text-sm text-gray-400">Loading grocery list…</div>;
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4 text-sm text-gray-400">
        Grocery list will appear once you have meals planned for this week.
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4 text-sm text-gray-400">
        No ingredients yet. Assign recipes to build your grocery list.
      </div>
    );
  }

  const checkedCount = data.items.filter((i) => checked[i.name]).length;
  const summary = data.budget_summary;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-700">Grocery List</h3>
        <span className="text-xs text-gray-400">
          {checkedCount}/{data.items.length} checked
        </span>
      </div>

      {summary.budget > 0 && (
        <div className={`rounded-lg px-3 py-2 text-sm ${summary.over_budget ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-800"}`}>
          <div className="flex justify-between font-medium">
            <span>Estimated total</span>
            <span>${summary.estimated_total.toFixed(2)} / ${summary.budget.toFixed(2)}</span>
          </div>
          {summary.zip_code && (
            <p className="text-xs mt-1 opacity-80">
              Estimated Walmart prices for ZIP {summary.zip_code}
            </p>
          )}
          {summary.prices_as_of && (
            <p className="text-xs mt-1 opacity-80">
              Prices as of {summary.prices_as_of.slice(0, 10)}
              {summary.stale ? " (estimated)" : ""}
            </p>
          )}
        </div>
      )}

      <div className="space-y-4">
        {data.categories.map((category) => (
          <div key={category.name}>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
                {category.name}
              </h4>
              {category.subtotal != null && category.subtotal > 0 && (
                <span className="text-xs text-gray-400">${category.subtotal.toFixed(2)}</span>
              )}
            </div>
            <ul className="space-y-1">
              {category.items.map((item) => (
                <li key={item.name}>
                  <label className="flex items-start gap-2 text-sm cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={!!checked[item.name]}
                      onChange={() => toggle(item.name)}
                      className="mt-0.5 rounded border-gray-300 text-emerald-500 focus:ring-emerald-400"
                    />
                    <span className={`flex-1 ${checked[item.name] ? "line-through text-gray-400" : "text-gray-700"}`}>
                      <span className="flex justify-between gap-2">
                        <span>
                          {item.name}
                          {item.stale && <span className="text-amber-500"> *</span>}
                        </span>
                        {formatPrice(item.price) && (
                          <span className="text-xs text-gray-500 shrink-0">{formatPrice(item.price)}</span>
                        )}
                      </span>
                      {item.recipes.length > 0 && (
                        <span className="block text-xs text-gray-400 group-hover:text-gray-500">
                          {item.recipes.join(", ")}
                        </span>
                      )}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
