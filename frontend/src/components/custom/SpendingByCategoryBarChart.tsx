// frontend/src/components/custom/SpendingByCategoryBarChart.tsx
'use client';

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Empty, EmptyMedia, EmptyTitle, EmptyDescription } from '@/components/ui/empty';
import { BarChart as BarChartIcon } from 'lucide-react';

// Helper to format numbers as currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

const COLORS = [
  'hsl(217, 91%, 60%)',
  'hsl(142, 76%, 36%)',
  'hsl(0, 84%, 60%)',
  '#FFBB28',
  '#8884d8',
  '#ff4d4d',
];

export function SpendingByCategoryBarChart({ data }: { data: Array<{ category: string; total: number }> }) {
  if (!data || data.length === 0) {
    return (
      <Card className="h-full border-border/40 shadow-sm hover:shadow-md transition-shadow">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl">Spending by Category</CardTitle>
          <CardDescription className="mt-1.5">Breakdown of your spending by category</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center h-[350px] text-muted-foreground gap-3">
            <BarChartIcon className="h-10 w-10" />
            <p className="text-sm">No spending data for the selected period.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full border-border/40 shadow-sm hover:shadow-md transition-shadow">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl">Spending by Category</CardTitle>
        <CardDescription className="mt-1.5">Breakdown of your spending by category</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[350px]">
          <ResponsiveContainer width="100%" height={350}>
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 20, right: 30, left: 40, bottom: 20 }}
              barCategoryGap={20}
            >
              <XAxis type="number" tickFormatter={formatCurrency} stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis type="category" dataKey="category" stroke="hsl(var(--muted-foreground))" fontSize={14} width={120} />
              <Tooltip formatter={(value) => formatCurrency(value as number)} />
              <Bar dataKey="total" name="Spending" radius={[8, 8, 8, 8]}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
