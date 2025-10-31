// frontend/src/components/custom/CashFlowChart.tsx
'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { type DateRange } from 'react-day-picker';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Bar, ComposedChart, Line, ResponsiveContainer, XAxis, YAxis, CartesianGrid } from 'recharts';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  ChartConfig,
} from '@/components/ui/chart';
import { format, parse, startOfMonth, endOfMonth } from 'date-fns';
import { Empty, EmptyMedia, EmptyTitle, EmptyDescription } from '@/components/ui/empty';
import { BarChart as BarChartIcon, CircleDashed, TrendingUp, TrendingDown } from 'lucide-react';

type CashFlowData = {
  month: string;
  total_income: number;
  total_spending: number;
  net_flow: number;
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

// Enhanced config with better colors
const chartConfig = {
  income: { 
    label: "Income", 
    color: "hsl(142, 76%, 36%)" // Rich green
  },
  spending: { 
    label: "Spending", 
    color: "hsl(0, 84%, 60%)" // Warm red
  },
  netFlow: { 
    label: "Net Flow", 
    color: "hsl(217, 91%, 60%)" // Vibrant blue
  },
} satisfies ChartConfig;

export function CashFlowChart({ dateRange }: { dateRange: DateRange | undefined }) {
  const { getToken } = useAuth();
  const router = useRouter(); 
  const [chartData, setChartData] = useState<CashFlowData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Calculate summary stats
  const totalIncome = chartData.reduce((sum, item) => sum + item.total_income, 0);
  const totalSpending = chartData.reduce((sum, item) => sum + item.total_spending, 0);
  const netTotal = totalIncome - totalSpending;
  const isPositive = netTotal >= 0;

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

        const processedData = data.map((item: any) => ({
          ...item,
          net_flow: item.total_income - item.total_spending,
        }));
        setChartData(processedData);

      } catch (error) {
        console.error(error);
        setChartData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCashFlowData();
  }, [dateRange, getToken]);

  const handleBarClick = (data: CashFlowData) => {
    if (!data || !data.month) return;
    const monthString = data.month;
    const monthDate = parse(monthString, 'MMM yyyy', new Date());
    const startDate = format(startOfMonth(monthDate), 'yyyy-MM-dd');
    const endDate = format(endOfMonth(monthDate), 'yyyy-MM-dd');
    router.push(`/transactions?start_date=${startDate}&end_date=${endDate}`);
  };

  return (
    <Card className="h-full border-border/40 shadow-sm hover:shadow-md transition-shadow">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl">Monthly Cash Flow</CardTitle>
            <CardDescription className="mt-1.5">
              Income vs. spending over the selected period
            </CardDescription>
          </div>
          {!isLoading && chartData.length > 0 && (
            <div className="text-right">
              <div className="text-sm text-muted-foreground mb-1">Net Total</div>
              <div className={`text-2xl font-bold flex items-center gap-1.5 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                {isPositive ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
                {formatCurrency(netTotal)}
              </div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-[350px] text-muted-foreground gap-3">
            <CircleDashed className="h-10 w-10 animate-spin text-primary/60" />
            <p className="text-sm">Loading cash flow data...</p>
          </div>
        ) : chartData.length === 0 ? (
          <Empty className="h-[350px]">
            <EmptyMedia><BarChartIcon className="h-12 w-12" /></EmptyMedia>
            <EmptyTitle>No Data Available</EmptyTitle>
            <EmptyDescription>
              There is no transaction data for the selected period.
            </EmptyDescription>
          </Empty>
        ) : (
          <ChartContainer config={chartConfig} className="w-full h-[350px]">
            <ComposedChart data={chartData} accessibilityLayer margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(142, 76%, 36%)" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="hsl(142, 76%, 36%)" stopOpacity={0.6} />
                </linearGradient>
                <linearGradient id="spendingGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.6} />
                </linearGradient>
              </defs>
              <CartesianGrid 
                strokeDasharray="3 3" 
                stroke="hsl(var(--border))" 
                opacity={0.3}
                vertical={false}
              />
              <XAxis 
                dataKey="month" 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={12} 
                tickLine={false} 
                axisLine={false}
                dy={10}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={12} 
                tickLine={false} 
                axisLine={false}
                tickFormatter={(value) => `$${value.toLocaleString()}`}
                dx={-10}
              />
              <ChartTooltip
                cursor={{ fill: 'hsl(var(--muted))', opacity: 0.1 }}
                content={<ChartTooltipContent formatter={(value) => formatCurrency(value as number)} />}
              />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar 
                dataKey="total_income" 
                name="Income" 
                fill="url(#incomeGradient)"
                radius={[8, 8, 0, 0]} 
                onClick={handleBarClick} 
                className="cursor-pointer hover:opacity-80 transition-opacity"
                maxBarSize={60}
              />
              <Bar 
                dataKey="total_spending" 
                name="Spending" 
                fill="url(#spendingGradient)"
                radius={[8, 8, 0, 0]} 
                onClick={handleBarClick} 
                className="cursor-pointer hover:opacity-80 transition-opacity"
                maxBarSize={60}
              />
              <Line 
                type="monotone" 
                dataKey="net_flow" 
                name="Net Flow" 
                stroke="hsl(217, 91%, 60%)" 
                strokeWidth={3} 
                dot={{ 
                  r: 5, 
                  fill: "hsl(217, 91%, 60%)",
                  strokeWidth: 2,
                  stroke: "hsl(var(--background))"
                }}
                activeDot={{ 
                  r: 7,
                  fill: "hsl(217, 91%, 60%)",
                  strokeWidth: 2,
                  stroke: "hsl(var(--background))"
                }}
              />
            </ComposedChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}