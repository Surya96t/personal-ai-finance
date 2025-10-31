// frontend/src/hooks/useDashboardSummary.ts
'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { type DateRange } from 'react-day-picker';
import { subDays } from 'date-fns';

// --- THIS IS THE UPDATED INTERFACE ---
export interface SummaryData {
  total_spending: number;
  total_income: number;
  spending_by_category: { category: string; total: number }[];
  savings_rate: number;
  average_daily_spending: number;
  avg_daily_spending_change: number;
  daily_spending_trend: { date: string; spending: number }[];
  // New fields from the API
  income_change: number;
  spending_change: number;
  total_transactions_count: number;
  income_transactions_count: number;
  expense_transactions_count: number;
}


export function useDashboardSummary() {
  const { getToken } = useAuth();
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Set default date range to the last 30 days
  const [dateRange, setDateRange] = useState<DateRange | undefined>({
    from: subDays(new Date(), 29),
    to: new Date(),
  });

  const fetchData = useCallback(async () => {
    if (!dateRange?.from || !dateRange?.to) return;
    
    setIsLoading(true);
    try {
      const token = await getToken();
      
      // Format dates to YYYY-MM-DD for the API query
      const startDate = dateRange.from.toISOString().split('T')[0];
      const endDate = dateRange.to.toISOString().split('T')[0];

      const response = await fetch(
        `http://127.0.0.1:8000/api/v1/dashboard/summary?start_date=${startDate}&end_date=${endDate}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!response.ok) throw new Error('Failed to fetch summary data.');

      const data: SummaryData = await response.json();
      setSummaryData(data);
    } catch (error) {
      console.error(error);
      setSummaryData(null); // Clear data on error
    } finally {
      setIsLoading(false);
    }
  }, [dateRange, getToken]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { summaryData, isLoading, dateRange, setDateRange };
}