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
        Diet and allergen settings filter recipe search and auto-generate suggestions.
      </p>

      <form
        onSubmit={(e) => { e.preventDefault(); save.mutate(form); }}
        className="space-y-6"
      >
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
          {form.allergens.length > 0 && (
            <p className="text-xs text-gray-400">
              Recipes containing {form.allergens.join(", ")} will be filtered out of all searches.
            </p>
          )}
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
