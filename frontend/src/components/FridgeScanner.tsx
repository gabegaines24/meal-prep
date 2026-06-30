import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { scanFridge } from "../api/scan";
import type { ScanResult } from "../api/scan";
import RecipeCard from "./RecipeCard";

export default function FridgeScanner() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }

  function handleInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }

  function processFile(file: File) {
    setError(null);
    setResult(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    runScan(file);
  }

  async function runScan(file: File) {
    setScanning(true);
    try {
      const data = await scanFridge(file);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Drop zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className="border-2 border-dashed border-gray-300 hover:border-emerald-400 rounded-xl p-10 flex flex-col items-center justify-center gap-3 cursor-pointer transition-colors"
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleInput}
        />
        {preview ? (
          <img src={preview} alt="Fridge preview" className="max-h-56 rounded-lg object-contain" />
        ) : (
          <>
            <span className="text-4xl">📷</span>
            <p className="text-gray-500 text-sm text-center">
              Drop a fridge photo here, or click to upload
            </p>
          </>
        )}
      </div>

      {scanning && (
        <div className="text-center text-emerald-600 font-medium animate-pulse">
          Scanning with Claude…
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-5">
          {/* Ingredients */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-2">Detected Ingredients</h3>
            {result.ingredients.length === 0 ? (
              <p className="text-sm text-gray-400">No ingredients detected.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {result.ingredients.map((ing) => (
                  <span
                    key={ing}
                    className="bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full px-3 py-1 text-xs font-medium"
                  >
                    {ing}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Suggested recipes */}
          {result.recipes.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-700 mb-3">Suggested Recipes</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {result.recipes.map((r) => (
                  <RecipeCard key={r.id} recipe={r} />
                ))}
              </div>
            </div>
          )}

          {result.ingredients.length > 0 && result.agent_prompt && (
            <button
              onClick={() =>
                navigate("/chat", {
                  state: {
                    initialMessage: result.agent_prompt,
                    scanIngredients: result.ingredients,
                  },
                })
              }
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
            >
              Plan meals with Copilot →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
