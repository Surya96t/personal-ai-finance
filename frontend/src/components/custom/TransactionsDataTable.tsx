// frontend/src/components/custom/TransactionsDataTable.tsx
'use client';

import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@clerk/nextjs';
import { format } from 'date-fns';
import { type DateRange } from 'react-day-picker';
import { useDebounce } from '@/hooks/useDebounce';
import { DateRangePicker } from './DateRangePicker';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { Search } from 'lucide-react';
import { Spinner } from '@/components/ui/spinner';
import { InputGroup, InputGroupAddon } from '@/components/ui/input-group';
import { Empty, EmptyMedia, EmptyTitle, EmptyDescription } from '@/components/ui/empty';
import { ListX } from 'lucide-react';

// Define the TypeScript type for a single transaction
type Transaction = {
  id: string;
  date: string;
  cleaned_description: string | null;
  description: string;
  category: string;
  amount: number;
};

// Helper to format numbers as currency
const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

export function TransactionsDataTable() {
  const { getToken } = useAuth();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State for filter controls
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [dateRange, setDateRange] = useState<DateRange | undefined>(undefined);

  // State to track which transaction is being updated
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  // Use our custom hook to debounce the search term
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  // Data fetching logic
  useEffect(() => {
    const fetchTransactions = async () => {
      setIsLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (debouncedSearchTerm) params.append('query', debouncedSearchTerm);
      if (selectedCategory) params.append('category', selectedCategory);
      if (dateRange?.from) params.append('start_date', format(dateRange.from, 'yyyy-MM-dd'));
      if (dateRange?.to) params.append('end_date', format(dateRange.to, 'yyyy-MM-dd'));
      
      const url = `http://127.0.0.1:8000/api/v1/transactions?${params.toString()}`;

      try {
        const token = await getToken();
        if (!token) throw new Error("User is not authenticated.");
        const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch transactions.');
        }
        const data: Transaction[] = await response.json();
        setTransactions(data);
      } catch (err) {
        setError((err as Error).message);
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTransactions();
  }, [getToken, debouncedSearchTerm, selectedCategory, dateRange]);

  // Dynamically get category list from the data we've fetched
  const categories = useMemo(() => {
    const uniqueCategories = new Set(transactions.map(t => t.category));
    return Array.from(uniqueCategories).filter(category => category && category.trim() !== '').sort();
  }, [transactions]);

  // Handler function for the main category filter
  const handleCategoryChange = (value: string) => {
    setSelectedCategory(value === "all" ? "" : value);
  };

  // Handler function for inline category updates
  const handleCategoryUpdate = async (transactionId: string, newCategory: string) => {
    setUpdatingId(transactionId);
    try {
      const token = await getToken();
      const response = await fetch(`http://127.0.0.1:8000/api/v1/transactions/${transactionId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ category: newCategory }),
      });

      if (!response.ok) throw new Error('Failed to update category.');

      setTransactions((current) =>
        current.map((trx) =>
          trx.id === transactionId ? { ...trx, category: newCategory } : trx
        )
      );

      toast.success("Category updated successfully!");
    } catch (err) {
      toast.error("Update Failed", { description: (err as Error).message });
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <Card>
      {/* Filter Controls UI */}
      <div className="p-4 flex flex-wrap items-center gap-4 border-b">
        <InputGroup className="max-w-sm">
          <InputGroupAddon>
            <Search className="h-4 w-4" />
          </InputGroupAddon>
          <Input
            placeholder="Search descriptions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </InputGroup>
        <Select value={selectedCategory || "all"} onValueChange={handleCategoryChange}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map((category) => (
              <SelectItem key={category} value={category}>{category}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DateRangePicker date={dateRange} onDateChange={setDateRange} />
      </div>

      {/* Data Table */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[150px]">Date</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="w-[220px]">Category</TableHead>
              <TableHead className="text-right w-[150px]">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={4} className="h-24 text-center">Loading transactions...</TableCell></TableRow>
            ) : error ? (
              <TableRow><TableCell colSpan={4} className="h-24 text-center text-red-500">Error: {error}</TableCell></TableRow>
            ) : transactions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="py-12">
                  <Empty>
                    <EmptyMedia><ListX /></EmptyMedia>
                    <EmptyTitle>No Transactions Found</EmptyTitle>
                    <EmptyDescription>
                      No transactions match your current filters.
                    </EmptyDescription>
                  </Empty>
                </TableCell>
              </TableRow>
            ) : (
              transactions.map((transaction) => (
                <TableRow key={transaction.id}>
                  <TableCell>{format(new Date(transaction.date), 'MMM dd, yyyy')}</TableCell>
                  <TableCell className="font-medium">
                    {transaction.cleaned_description || transaction.description}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {updatingId === transaction.id && <Spinner className="h-4 w-4" />}
                      <Select
                        value={transaction.category}
                        onValueChange={(newCategory) => handleCategoryUpdate(transaction.id, newCategory)}
                        disabled={updatingId === transaction.id}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {categories.map((category) => (
                            <SelectItem key={category} value={category}>{category}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </TableCell>
                  <TableCell
                    className={cn(
                      'text-right font-mono',
                      transaction.amount >= 0 ? 'text-green-600' : 'text-slate-800'
                    )}
                  >
                    {transaction.amount >= 0 ? '+' : ''}{formatCurrency(transaction.amount)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}