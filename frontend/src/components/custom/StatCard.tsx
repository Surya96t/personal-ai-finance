// frontend/src/components/custom/StatCard.tsx

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { ArrowDown, ArrowUp } from "lucide-react";

// Helper to format currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

type StatCardFormat = 'currency' | 'percentage' | 'number';
type SparklineData = { date: string; value: number }[];

interface StatCardProps {
  title: string;
  // --- THE FIX: The value prop is now optional ---
  value?: number;
  icon: React.ElementType;
  format?: StatCardFormat;
  colorFn?: (value: number) => string;
  change?: number;
  sparklineData?: SparklineData;
  description?: string;
}

export function StatCard({ title, value = 0, icon: Icon, format = 'currency', colorFn, change, sparklineData, description }: StatCardProps) {
  // --- THE FIX: Default the value to 0 if it's not provided ---

  const formattedValue =
    format === 'percentage' ? `${value.toFixed(2)}%`
    : format === 'currency' ? formatCurrency(value)
    : value.toLocaleString(); // This is now safe because value will always be a number

  const colorClass = colorFn ? colorFn(value) : '';
  const hasChange = change !== undefined && change !== null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-start justify-between">
            <div className="flex flex-col">
                <div className={cn("text-2xl font-bold", colorClass)}>
                  {formattedValue}
                </div>
                {description && (
                    <p className="text-xs text-muted-foreground">{description}</p>
                )}
                {hasChange && (
                    <p className="text-xs text-muted-foreground flex items-center">
                        {change > 0 ? (
                            <ArrowUp className="h-4 w-4 text-green-500" />
                        ) : change < 0 ? (
                            <ArrowDown className="h-4 w-4 text-red-500" />
                        ) : null}
                        {change.toFixed(2)}% from last period
                    </p>
                )}
            </div>
            {sparklineData && (
                <div className="h-10 w-24">
                   <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={sparklineData}>
                            <defs>
                                <linearGradient id="sparkline-color" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.4}/>
                                    <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0.1}/>
                                </linearGradient>
                            </defs>
                            <Area type="monotone" dataKey="value" stroke="hsl(var(--chart-1))" fill="url(#sparkline-color)" strokeWidth={2}/>
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
      </CardContent>
    </Card>
  );
}