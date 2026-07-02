import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getProfile, updateProfile } from "../api/profile";
import type { Profile } from "../api/profile";

const DIET_OPTIONS = [
  { value: "", label: "No restriction" },
  { value: "gluten free", label: "Gluten Free" },
  { value: "ketogenic", label: "Ketogenic" },
  { value: "vegetarian", label: "Vegetarian" },
  { value: "vegan", label: "Vegan" },
  { value: "pescetarian", label: "Pescetarian" },
  { value: "paleo", label: "Paleo" },
  { value: "primal", label: "Primal" },
  { value: "whole30", label: "Whole30" },
];

const ALLERGEN_OPTIONS = [
  "dairy", "egg", "gluten", "grain", "peanut",
  "seafood", "sesame", "shellfish", "soy", "sulfite", "tree nut", "wheat",
];

const DEFAULT: Profile = {
  zip_code: "",
  weekly_budget: 0,
  allergens: [],
  diet_type: "",
};

export default function ProfilePage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const [form, setForm] = useState<Profile>(DEFAULT);
  const [saved, setSaved] = useState(false);

  useEffect(() => { if (data) setForm(data); }, [data]);

  const save = useMutation({
    mutationFn: updateProfile,
    onSuccess: (updated) => {
      qc.setQueryData(["profile"], updated);
      qc.invalidateQueries({ queryKey: ["recipes"] });
      qc.invalidateQueries({ queryKey: ["budget-summary"] });
      qc.invalidateQueries({ queryKey: ["grocery-list"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
  });

  function toggleAllergen(a: string) {
    setForm((f) => ({
      ...f,
      allergens: f.allergens.includes(a)
        ? f.allergens.filter((x) => x !== a)
        : [...f.allergens, a],
    }));
  }

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-800">My Profile</h1>
      <p className="text-sm text-gray-500">
        Diet, allergens, zip, and budget settings filter recipe search and grocery pricing.
      </p>

      <form
        onSubmit={(e) => { e.preventDefault(); save.mutate(form); }}
        className="space-y-6"
      >
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
          <h2 className="font-semibold text-gray-700">Location & Budget</h2>

          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Zip code</label>
            <input
              type="text"
              placeholder="e.g. 30309"
              value={form.zip_code}
              onChange={(e) => setForm((f) => ({ ...f, zip_code: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
            />
            <p className="text-xs text-gray-400 mt-1">
              Used for estimated Walmart grocery prices in your area.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              Weekly grocery budget <span className="text-gray-400 font-normal">(USD)</span>
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
              <input
                type="number"
                min={0}
                step={5}
                value={form.weekly_budget || ""}
                onChange={(e) => setForm((f) => ({ ...f, weekly_budget: Number(e.target.value) || 0 }))}
                className="w-full border border-gray-200 rounded-lg pl-7 pr-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Recipe search filters to ~${form.weekly_budget ? (form.weekly_budget / 21).toFixed(2) : "—"}/meal.
              Grocery prices use Walmart estimates via Apify. Amounts are approximate.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
          <h2 className="font-semibold text-gray-700">Diet Type</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {DIET_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => setForm((f) => ({ ...f, diet_type: value }))}
                className={`text-sm py-2 px-3 rounded-lg border transition-colors text-left ${
                  form.diet_type === value
                    ? "bg-emerald-500 text-white border-emerald-500"
                    : "border-gray-200 text-gray-600 hover:border-emerald-300"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
          <h2 className="font-semibold text-gray-700">Allergens to Avoid</h2>
          <div className="flex flex-wrap gap-2">
            {ALLERGEN_OPTIONS.map((a) => (
              <button
                key={a}
                type="button"
                onClick={() => toggleAllergen(a)}
                className={`capitalize text-sm px-3 py-1.5 rounded-full border transition-colors ${
                  form.allergens.includes(a)
                    ? "bg-red-500 text-white border-red-500"
                    : "border-gray-200 text-gray-600 hover:border-red-300"
                }`}
              >
                {a}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={save.isPending}
          className="w-full bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors"
        >
          {save.isPending ? "Saving…" : saved ? "Saved ✓" : "Save Profile"}
        </button>
      </form>
    </div>
  );
}
