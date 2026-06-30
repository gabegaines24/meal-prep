import { NavLink, Route, Routes } from "react-router-dom";
import Planner from "./pages/Planner";
import Goals from "./pages/Goals";
import Scanner from "./pages/Scanner";
import ProfilePage from "./pages/Profile";
import Chat from "./pages/Chat";

const NAV = [
  { to: "/", label: "Planner" },
  { to: "/chat", label: "Copilot" },
  { to: "/goals", label: "Goals" },
  { to: "/scanner", label: "Fridge Scanner" },
  { to: "/profile", label: "Profile" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-800">
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6">
          <span className="text-xl font-bold text-emerald-600">Meal Prep</span>
          <nav className="flex gap-4">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  isActive
                    ? "text-emerald-600 font-semibold"
                    : "text-gray-500 hover:text-gray-700"
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Planner />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/goals" element={<Goals />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </main>
    </div>
  );
}
