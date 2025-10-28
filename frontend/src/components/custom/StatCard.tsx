// frontend/src/components/custom/StatCard.tsx

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Helper to format numbers as currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

// We are making the value prop a number for better type safety
interface StatCardProps {
  title: string;
  value: number;
  icon: React.ElementType;
}

export function StatCard({ title, value, icon: Icon }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{formatCurrency(value)}</div>
      </CardContent>
    </Card>
  );
}