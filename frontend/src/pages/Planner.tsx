import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import WeeklyPlanner from "../components/WeeklyPlanner";
import MacroSummary from "../components/MacroSummary";
import BudgetTracker from "../components/BudgetTracker";
import { downloadGroceryList, downloadRecipeBook } from "../api/files";

export default function Planner() {
  const [emailStatus, setEmailStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const sendEmail = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/email/send", { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onMutate: () => setEmailStatus("sending"),
    onSuccess: () => {
      setEmailStatus("sent");
      setTimeout(() => setEmailStatus("idle"), 3000);
    },
    onError: () => {
      setEmailStatus("error");
      setTimeout(() => setEmailStatus("idle"), 3000);
    },
  });

  const [downloading, setDownloading] = useState<"grocery" | "recipe" | null>(null);

  async function handleDownload(type: "grocery" | "recipe") {
    setDownloading(type);
    try {
      if (type === "grocery") await downloadGroceryList();
      else await downloadRecipeBook();
    } catch (e) {
      console.error(e);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="space-y-6">
      <BudgetTracker />
      <WeeklyPlanner />

      {/* Action bar */}
      <div className="flex flex-wrap gap-3 pt-2 border-t border-gray-100">
        <button
          onClick={() => handleDownload("grocery")}
          disabled={downloading === "grocery"}
          className="flex items-center gap-2 bg-white border border-gray-200 hover:border-emerald-400 text-gray-700 text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          {downloading === "grocery" ? "Downloading…" : "⬇ Grocery List"}
        </button>

        <button
          onClick={() => handleDownload("recipe")}
          disabled={downloading === "recipe"}
          className="flex items-center gap-2 bg-white border border-gray-200 hover:border-emerald-400 text-gray-700 text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          {downloading === "recipe" ? "Downloading…" : "⬇ Recipe Book"}
        </button>

        <button
          onClick={() => sendEmail.mutate()}
          disabled={emailStatus === "sending"}
          className={`flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50 ${
            emailStatus === "sent"
              ? "bg-emerald-500 text-white"
              : emailStatus === "error"
              ? "bg-red-500 text-white"
              : "bg-emerald-500 hover:bg-emerald-600 text-white"
          }`}
        >
          {emailStatus === "sending"
            ? "Sending…"
            : emailStatus === "sent"
            ? "✓ Emailed!"
            : emailStatus === "error"
            ? "Failed — retry?"
            : "✉ Email My Plan"}
        </button>
      </div>

      <MacroSummary />
    </div>
  );
}
