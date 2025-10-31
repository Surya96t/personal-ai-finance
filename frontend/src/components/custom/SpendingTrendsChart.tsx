// frontend/src/components/custom/SpendingTrendsChart.tsx
'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { type DateRange } from 'react-day-picker';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Line, LineChart, XAxis, YAxis } from 'recharts';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartConfig,
} from '@/components/ui/chart';
import { format } from 'date-fns';
import { Empty, EmptyMedia, EmptyTitle, EmptyDescription } from '@/components/ui/empty';
import { CircleDashed, LineChart as LineChartIcon } from 'lucide-react';

// Define the structure of our data
type TrendsData = {
  date: string;
  total_spending: number;
};

// Helper to format currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

// Chart configuration for Shadcn wrapper components
const chartConfig = {
  spending: {
    label: "Spending",
    color: "hsl(var(--chart-1))",
  },
} satisfies ChartConfig;

export function SpendingTrendsChart({ dateRange }: { dateRange: DateRange | undefined }) {
  const { getToken } = useAuth();
  const [chartData, setChartData] = useState<TrendsData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // State and effect to resolve the CSS variable for the line color
  const [lineColor, setLineColor] = useState("hsl(var(--chart-1))");

  useEffect(() => {
    const resolvedColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--chart-1')
      .trim();
    if (resolvedColor) {
      setLineColor(`hsl(${resolvedColor})`);
    }
  }, []);

  // Data fetching logic
  useEffect(() => {
    if (!dateRange?.from || !dateRange?.to) {
      setIsLoading(false);
      setChartData([]);
      return;
    }

    const fetchTrendsData = async () => {
      setIsLoading(true);
      try {
        const token = await getToken();
        if (!token) throw new Error("Not authenticated");
        
        const startDate = format(dateRange.from!, 'yyyy-MM-dd');
        const endDate = format(dateRange.to!, 'yyyy-MM-dd');

        const response = await fetch(
          `http://127.0.0.1:8000/api/v1/dashboard/spending-trends?start_date=${startDate}&end_date=${endDate}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (!response.ok) throw new Error('Failed to fetch spending trends data.');

        const data: TrendsData[] = await response.json();
        setChartData(data);
      } catch (error) {
        console.error("Fetch error in SpendingTrendsChart:", error);
        setChartData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTrendsData();
  }, [dateRange, getToken]);

  return (
    <Card className="h-full border-border/40 shadow-sm hover:shadow-md transition-shadow">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl">Daily Spending Trend</CardTitle>
            <CardDescription className="mt-1.5">
              A line chart showing your spending for each day in the selected period.
            </CardDescription>
          </div>
          {!isLoading && chartData.length > 0 && (
            <div className="text-right">
              <div className="text-sm text-muted-foreground mb-1">Total Spending</div>
              <div className="text-2xl font-bold flex items-center gap-1.5 text-blue-600">
                {formatCurrency(chartData.reduce((sum, item) => sum + item.total_spending, 0))}
              </div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-[350px] text-muted-foreground gap-3">
            <CircleDashed className="h-10 w-10 animate-spin text-primary/60" />
            <p className="text-sm">Loading spending trends...</p>
          </div>
        ) : chartData.length === 0 ? (
          <Empty className="h-[350px]">
            <EmptyMedia><LineChartIcon className="h-12 w-12" /></EmptyMedia>
            <EmptyTitle>No Data Available</EmptyTitle>
            <EmptyDescription>
              There is no spending data for the selected period.
            </EmptyDescription>
          </Empty>
        ) : (
          <ChartContainer config={chartConfig} className="w-full h-[350px]">
            <LineChart data={chartData} width={undefined} height={350} accessibilityLayer margin={{ top: 5, right: 20, left: -10, bottom: 0 }}>
              <XAxis
                dataKey="date"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => format(new Date(value), 'MMM dd')}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => `$${value}`}
              />
              <ChartTooltip
                cursor={{ fill: 'hsl(var(--muted))', opacity: 0.1 }}
                content={<ChartTooltipContent formatter={(value) => formatCurrency(value as number)} />}
              />
              <Line
                type="monotone"
                dataKey="total_spending"
                name="Spending"
                stroke="hsl(217, 91%, 60%)"
                strokeWidth={3}
                dot={false}
              />
            </LineChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}