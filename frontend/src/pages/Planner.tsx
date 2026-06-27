import WeeklyPlanner from "../components/WeeklyPlanner";
import MacroSummary from "../components/MacroSummary";

export default function Planner() {
  return (
    <div className="space-y-8">
      <WeeklyPlanner />
      <MacroSummary />
    </div>
  );
}
