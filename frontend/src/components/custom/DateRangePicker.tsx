// frontend/src/components/custom/DateRangePicker.tsx
'use client';

import * as React from 'react';
import { Calendar as CalendarIcon } from 'lucide-react';
import { format, subDays, startOfYear } from 'date-fns';
import { type DateRange } from 'react-day-picker';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

interface DateRangePickerProps extends React.HTMLAttributes<HTMLDivElement> {
  date: DateRange | undefined;
  onDateChange: (date: DateRange | undefined) => void;
}

export function DateRangePicker({ className, date, onDateChange }: DateRangePickerProps) {
  const currentYear = new Date().getFullYear();

  return (
    <div className={cn('grid gap-2', className)}>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant={'outline'}
            className={cn(
              'w-[300px] justify-start text-left font-normal',
              !date && 'text-muted-foreground'
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {date?.from ? (
              date.to ? (
                <>
                  {format(date.from, 'LLL dd, y')} - {format(date.to, 'LLL dd, y')}
                </>
              ) : (
                format(date.from, 'LLL dd, y')
              )
            ) : (
              <span>Pick a date range</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0 flex" align="start">
          {/* --- Presets Sidebar --- */}
          <div className="flex flex-col space-y-2 border-r p-4">
            <Button
              variant="ghost"
              className="justify-start"
              onClick={() => onDateChange({ from: subDays(new Date(), 6), to: new Date() })}
            >
              Last 7 Days
            </Button>
            <Button
              variant="ghost"
              className="justify-start"
              onClick={() => onDateChange({ from: subDays(new Date(), 29), to: new Date() })}
            >
              Last 30 Days
            </Button>
            <Button
              variant="ghost"
              className="justify-start"
              onClick={() => onDateChange({ from: subDays(new Date(), 89), to: new Date() })}
            >
              Last 90 Days
            </Button>
             <Button
              variant="ghost"
              className="justify-start"
              onClick={() => onDateChange({ from: startOfYear(new Date()), to: new Date() })}
            >
              This Year
            </Button>
          </div>

          {/* --- Calendar with Year/Month Dropdowns --- */}
          <Calendar
            initialFocus
            mode="range"
            defaultMonth={date?.from}
            selected={date}
            onSelect={onDateChange}
            numberOfMonths={2}
            captionLayout="dropdown"
            fromYear={currentYear - 10}
            toYear={currentYear}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}