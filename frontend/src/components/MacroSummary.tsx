import { useQuery } from "@tanstack/react-query";
import { getWeek } from "../api/meals";
import { getGoals } from "../api/goals";

const MACROS = [
  { key: "calories" as const, label: "Calories", unit: "kcal", color: "bg-orange-400" },
  { key: "protein" as const, label: "Protein", unit: "g", color: "bg-blue-400" },
  { key: "carbs" as const, label: "Carbs", unit: "g", color: "bg-yellow-400" },
  { key: "fat" as const, label: "Fat", unit: "g", color: "bg-red-400" },
];

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const over = max > 0 && value > max;
  return (
    <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
      <div
        className={`absolute left-0 top-0 h-full rounded-full transition-all ${over ? "bg-red-500" : color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function MacroSummary() {
  const { data: week } = useQuery({ queryKey: ["week"], queryFn: () => getWeek() });
  const { data: goals } = useQuery({ queryKey: ["goals"], queryFn: getGoals });

  if (!week || !goals) return null;

  const weekly = week.weekly_macros;
  const weeklyGoals = {
    calories: goals.calories * 7,
    protein: goals.protein * 7,
    carbs: goals.carbs * 7,
    fat: goals.fat * 7,
  };

  return (
    <div className="space-y-6">
      {/* Weekly totals */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <h3 className="font-semibold text-gray-700 mb-3">Weekly Macros</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {MACROS.map(({ key, label, unit, color }) => (
            <div key={key}>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{label}</span>
                <span>
                  {weekly[key].toFixed(0)} / {weeklyGoals[key].toFixed(0)} {unit}
                </span>
              </div>
              <Bar value={weekly[key]} max={weeklyGoals[key]} color={color} />
            </div>
          ))}
        </div>
      </div>

      {/* Daily breakdown */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <h3 className="font-semibold text-gray-700 mb-3">Daily Breakdown</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-gray-400">
                <th className="text-left pb-2 pr-4">Day</th>
                {MACROS.map(({ label, unit }) => (
                  <th key={label} className="text-right pb-2 px-2">
                    {label} ({unit})
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {week.daily_macros.map((day) => (
                <tr key={day.day}>
                  <td className="py-1.5 pr-4 font-medium text-gray-600">{day.day}</td>
                  {MACROS.map(({ key }) => {
                    const over = day[key] > goals[key];
                    return (
                      <td
                        key={key}
                        className={`text-right py-1.5 px-2 ${over ? "text-red-500 font-semibold" : "text-gray-700"}`}
                      >
                        {day[key].toFixed(0)}
                        {over && " ↑"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
