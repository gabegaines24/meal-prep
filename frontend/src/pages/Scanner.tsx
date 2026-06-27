import FridgeScanner from "../components/FridgeScanner";

export default function Scanner() {
  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <h1 className="text-xl font-bold text-gray-800">Fridge Scanner</h1>
      <p className="text-sm text-gray-500">
        Upload a photo of your fridge and Claude will identify the ingredients. We'll suggest
        recipes that use what you already have.
      </p>
      <FridgeScanner />
    </div>
  );
}
