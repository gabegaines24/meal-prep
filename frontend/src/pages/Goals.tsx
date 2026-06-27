import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getGoals, updateGoals } from "../api/goals";
import type { Goals } from "../api/goals";

const FIELDS: { key: keyof Goals; label: string; unit: string }[] = [
  { key: "calories", label: "Calories", unit: "kcal/day" },
  { key: "protein", label: "Protein", unit: "g/day" },
  { key: "carbs", label: "Carbohydrates", unit: "g/day" },
  { key: "fat", label: "Fat", unit: "g/day" },
];

export default function GoalsPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["goals"], queryFn: getGoals });
  const [form, setForm] = useState<Goals>({ calories: 2000, protein: 150, carbs: 200, fat: 65 });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = useMutation({
    mutationFn: updateGoals,
    onSuccess: (updated) => {
      qc.setQueryData(["goals"], updated);
      qc.invalidateQueries({ queryKey: ["week"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-xl font-bold text-gray-800 mb-6">Daily Macro Goals</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(form);
        }}
        className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-5"
      >
        {FIELDS.map(({ key, label, unit }) => (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              {label} <span className="text-gray-400 font-normal">({unit})</span>
            </label>
            <input
              type="number"
              min={0}
              step={key === "calories" ? 50 : 5}
              value={form[key]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: Number(e.target.value) }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
            />
          </div>
        ))}

        <button
          type="submit"
          disabled={save.isPending}
          className="w-full bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition-colors"
        >
          {save.isPending ? "Saving…" : saved ? "Saved ✓" : "Save Goals"}
        </button>
      </form>

      <p className="mt-4 text-xs text-gray-400 text-center">
        Changes apply immediately to the macro summary on the Planner page.
      </p>
    </div>
  );
}
