// frontend/src/app/transactions/page.tsx
import { TransactionsDataTable } from "@/components/custom/TransactionsDataTable";

export default function TransactionsPage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">All Transactions</h1>
      <TransactionsDataTable />
    </div>
  );
}