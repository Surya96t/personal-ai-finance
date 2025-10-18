// frontend/src/app/dashboard/page.tsx
'use client';

import { DocumentUpload } from '@/components/custom/DocumentUpload';
import { DateRangePicker } from '@/components/custom/DateRangePicker';
import { useDashboardSummary, type SummaryData } from '@/hooks/useDashboardSummary';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DollarSign, TrendingDown, TrendingUp } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { RecentDocumentsList } from '@/components/custom/RecentDocumentsList'; 


// Helper to format numbers as currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

// Stat Card Component
function StatCard({ title, value, icon: Icon }: { title: string; value: string; icon: React.ElementType }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}

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

// Main Dashboard Page
export default function DashboardPage() {
  const { summaryData, isLoading, dateRange, setDateRange } = useDashboardSummary();

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <DateRangePicker date={dateRange} onDateChange={setDateRange} />
      </div>

      {isLoading ? (
        <p>Loading summary...</p>
      ) : summaryData ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <StatCard
              title="Total Income"
              value={formatCurrency(summaryData.total_income)}
              icon={TrendingUp}
            />
            <StatCard
              title="Total Spending"
              value={formatCurrency(summaryData.total_spending)}
              icon={TrendingDown}
            />
            <StatCard
              title="Net Flow"
              value={formatCurrency(summaryData.total_income - summaryData.total_spending)}
              icon={DollarSign}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
            <Card className="col-span-4">
              <CardHeader>
                <CardTitle>Spending by Category</CardTitle>
              </CardHeader>
              <CardContent>
                {summaryData.spending_by_category.length > 0 ? (
                  <SpendingPieChart data={summaryData.spending_by_category} />
                ) : (
                  <p>No spending data for this period.</p>
                )}
              </CardContent>
            </Card>

            <div className="col-span-3">
               <DocumentUpload />
               <RecentDocumentsList />
            </div>
          </div>
        </>
      ) : (
        <p>Could not load summary data.</p>
      )}
    </div>
  );
}