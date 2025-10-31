// frontend/src/components/custom/MetricCard.tsx

import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { MoreVertical, TrendingUp, TrendingDown, DollarSign } from "lucide-react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";

// Helper to format numbers as currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);

interface MetricCardProps {
  title: string;
  value: number;
  trendPercent: number;
  comparisonText: string;
  chartData: { value: number }[];
  periodLabel?: string;
  icon?: React.ElementType; // Add icon prop
}

export function MetricCard({
  title,
  value,
  trendPercent,
  comparisonText,
  chartData,
  periodLabel = "View 24 hours",
  icon: Icon = DollarSign, // Default to DollarSign
}: MetricCardProps) {
  const isPositive = trendPercent >= 0;
  const TrendIcon = isPositive ? TrendingUp : TrendingDown;
  const trendColor = isPositive ? "text-green-600" : "text-red-600";

  return (
    <Card className="relative overflow-visible rounded-xl shadow-lg bg-gradient-to-br from-white via-slate-50 to-green-50">
      <div className="absolute top-2 right-2 z-10">
        <Popover>
          <PopoverTrigger asChild>
            <button className="p-1 rounded hover:bg-muted transition">
              <MoreVertical className="h-5 w-5 text-muted-foreground" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-40 text-sm">
            <div className="py-2">More options coming soon</div>
          </PopoverContent>
        </Popover>
      </div>
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-xs font-semibold text-muted-foreground">
          {periodLabel}
        </CardTitle>
        <div className="rounded-full bg-green-100 p-2">
          <Icon className="h-6 w-6 text-green-600" />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-4xl font-extrabold tracking-tight">{formatCurrency(value)}</span>
          <span className={cn("flex items-center gap-1 text-lg font-semibold", trendColor)}>
            <TrendIcon className={cn("h-5 w-5", isPositive ? "animate-bounce" : "animate-pulse")}/>
            {Math.abs(trendPercent)}%
          </span>
        </div>
        <span className="block text-sm text-muted-foreground mb-2">{comparisonText}</span>
        <ResponsiveContainer width="100%" height={56}>
          <LineChart data={chartData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="sparklineGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Line
              type="monotone"
              dataKey="value"
              stroke="#22c55e"
              strokeWidth={3}
              dot={false}
              fill="url(#sparklineGradient)"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
