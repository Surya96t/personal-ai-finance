// frontend/src/app/(protected)/dashboard/page.tsx
'use client';

import { SpendingTrendsChart } from '@/components/custom/SpendingTrendsChart'; 
import { DateRangePicker } from '@/components/custom/DateRangePicker';
import { useDashboardSummary, type SummaryData } from '@/hooks/useDashboardSummary';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart as BarChartIcon, DollarSign, TrendingDown, TrendingUp, CreditCard, PiggyBank, List } from 'lucide-react';
import { MetricCard } from '@/components/custom/MetricCard';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from '@/components/ui/empty';
import { CashFlowChart } from '@/components/custom/CashFlowChart';
import { StatCard } from '@/components/custom/StatCard';

// Helper to format numbers as currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

// Pie Chart Component
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#ff4d4d'];
function SpendingPieChart({ data }: { data: SummaryData['spending_by_category'] }) {
  return (
    <ResponsiveContainer width="100%" height={350}>
      <PieChart>
        <Pie data={data} dataKey="total" nameKey="category" cx="50%" cy="50%" outerRadius={120} label>
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(value) => formatCurrency(value as number)} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

export default function DashboardPage() {
  const { summaryData, isLoading, dateRange, setDateRange } = useDashboardSummary();

  
  // console.log("SummaryData:", {summaryData})
  // --- NEW: Define the color logic for the savings rate ---
  const getSavingsRateColor = (rate: number): string => {
    if (rate > 20) return 'text-green-500';
    if (rate >= 10 && rate <= 20) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <DateRangePicker value={dateRange} onChange={setDateRange} />
      </div>

      {isLoading ? (
        <div className="text-center text-muted-foreground py-12">Loading summary...</div>
      ) : summaryData ? (
        <div className="space-y-8">
          
          {/* --- FINAL: Stat Cards Row now has 6 cards in a 3x2 grid --- */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <StatCard
              title="Total Income"
              value={summaryData.total_income}
              icon={TrendingUp}
              change={summaryData.income_change}
            />
            <StatCard
              title="Total Spending"
              value={summaryData.total_spending}
              icon={TrendingDown}
              change={summaryData.spending_change}
            />
            <StatCard
              title="Net Flow"
              value={summaryData.total_income - summaryData.total_spending}
              icon={DollarSign}
            />
            <StatCard
              title="Avg. Daily Spending"
              value={summaryData.average_daily_spending}
              icon={DollarSign}
              change={summaryData.avg_daily_spending_change}
            />
            <StatCard
              title="Savings Rate"
              value={summaryData.savings_rate}
              icon={PiggyBank}
              format="percentage"
              colorFn={getSavingsRateColor}
            />
            {/* --- THIS IS THE NEW CARD --- */}
            <StatCard
              title="Total Transactions"
              value={summaryData.total_transactions_count}
              icon={List}
              format="number"
              description={`${summaryData.income_transactions_count} income / ${summaryData.expense_transactions_count} expenses`}
            />
          </div>

          {/* New Main Grid for Charts */}
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-5">
            
            {/* Cash Flow Chart - taking up 3/5 of the width on large screens */}
            <div className="lg:col-span-3">
              <CashFlowChart dateRange={dateRange} />
            </div>

            {/* Spending by Category Chart - taking up 2/5 of the width */}
            <div className="lg:col-span-2">
              <Card className="h-full">
                <CardHeader>
                  <CardTitle>Spending by Category</CardTitle>
                </CardHeader>
                <CardContent>
                  {summaryData.spending_by_category.length > 0 ? (
                    <SpendingPieChart data={summaryData.spending_by_category} />
                  ) : (
                    <Empty className="h-[350px]">
                      <EmptyMedia><BarChartIcon /></EmptyMedia>
                      <EmptyTitle>No Spending Data</EmptyTitle>
                      <EmptyDescription>
                        There is no spending data for the selected period.
                      </EmptyDescription>
                    </Empty>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Spending Trends Chart - taking up the full width in its own row */}
          <div>
            <SpendingTrendsChart dateRange={dateRange} />
          </div>

        </div>
      ) : (
        <p className="text-center text-red-500 py-12">
          Could not load summary data. Please try again.
        </p>
      )}
    </div>
  );
}