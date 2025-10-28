// frontend/src/components/custom/CashFlowChart.tsx
'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { type DateRange } from 'react-day-picker';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Bar, BarChart, XAxis, YAxis } from 'recharts';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  ChartConfig,
} from '@/components/ui/chart';
import { format } from 'date-fns';
import { Empty, EmptyMedia, EmptyTitle, EmptyDescription } from '@/components/ui/empty';
import { BarChart as BarChartIcon, CircleDashed } from 'lucide-react';

// Define the structure of our cash flow data
type CashFlowData = {
  month: string;
  total_income: number;
  total_spending: number;
};

// Helper to format currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

// Define a ChartConfig for our chart
const chartConfig = {
  income: {
    label: "Income",
    color: "hsl(var(--chart-1))",
  },
  spending: {
    label: "Spending",
    color: "hsl(var(--chart-2))",
  },
} satisfies ChartConfig;


export function CashFlowChart({ dateRange }: { dateRange: DateRange | undefined }) {
  const { getToken } = useAuth();
  const [chartData, setChartData] = useState<CashFlowData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!dateRange?.from || !dateRange?.to) return;

    const fetchCashFlowData = async () => {
      setIsLoading(true);
      try {
        const token = await getToken();
        const startDate = format(dateRange.from!, 'yyyy-MM-dd');
        const endDate = format(dateRange.to!, 'yyyy-MM-dd');

        const response = await fetch(
          `http://127.0.0.1:8000/api/v1/dashboard/cashflow?start_date=${startDate}&end_date=${endDate}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (!response.ok) throw new Error('Failed to fetch cash flow data.');

        const data: CashFlowData[] = await response.json();
        setChartData(data);
      } catch (error) {
        console.error(error);
        setChartData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCashFlowData();
  }, [dateRange, getToken]);

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Monthly Cash Flow</CardTitle>
        <CardDescription>
          A summary of your income vs. spending over the selected period.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center h-[350px] text-muted-foreground">
            <CircleDashed className="h-8 w-8 animate-spin" />
          </div>
        ) : chartData.length === 0 ? (
          <Empty className="h-[350px]">
            <EmptyMedia><BarChartIcon /></EmptyMedia>
            <EmptyTitle>No Data Available</EmptyTitle>
            <EmptyDescription>
              There is no transaction data for the selected period.
            </EmptyDescription>
          </Empty>
        ) : (
          <ChartContainer config={chartConfig} className="w-full h-[350px]">
            <BarChart data={chartData} width={undefined} height={350} accessibilityLayer>
              <XAxis dataKey="month" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `$${value}`} />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent formatter={(value) => formatCurrency(value as number)} />}
              />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="total_income" name="Income" fill="var(--color-income)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="total_spending" name="Spending" fill="var(--color-spending)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}