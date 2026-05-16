import { RecordsTable } from "../components/RecordsTable";

export function RecordsPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Records History</h1>
        <p className="mt-1 text-sm text-gray-500">
          All processed messages. Auto-refreshes every 10 seconds. Export to Excel saves both JSON and .xlsx.
        </p>
      </div>
      <RecordsTable />
    </div>
  );
}
