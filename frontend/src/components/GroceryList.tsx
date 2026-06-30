import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchGroceryList } from "../api/files";

function checkedKey(weekStart: string, name: string) {
  return `grocery-checked:${weekStart}:${name}`;
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

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-700">Grocery List</h3>
        <span className="text-xs text-gray-400">
          {checkedCount}/{data.items.length} checked
        </span>
      </div>

      <div className="space-y-4">
        {data.categories.map((category) => (
          <div key={category.name}>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-600 mb-2">
              {category.name}
            </h4>
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
                    <span className={checked[item.name] ? "line-through text-gray-400" : "text-gray-700"}>
                      {item.name}
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
