"use client"

import { useState } from "react"
import {
  endOfMonth,
  endOfYear,
  startOfMonth,
  startOfYear,
  subDays,
  subMonths,
  subYears,
} from "date-fns"
import { DateRange } from "react-day-picker"

import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { format } from "date-fns"
import { CalendarIcon } from "lucide-react"

export function DateRangePicker() {
  const today = new Date()
  const yesterday = {
    from: subDays(today, 1),
    to: subDays(today, 1),
  }
  const last7Days = {
    from: subDays(today, 6),
    to: today,
  }
  const last30Days = {
    from: subDays(today, 29),
    to: today,
  }
  const monthToDate = {
    from: startOfMonth(today),
    to: today,
  }
  const lastMonth = {
    from: startOfMonth(subMonths(today, 1)),
    to: endOfMonth(subMonths(today, 1)),
  }
  const yearToDate = {
    from: startOfYear(today),
    to: today,
  }
  const lastYear = {
    from: startOfYear(subYears(today, 1)),
    to: endOfYear(subYears(today, 1)),
  }
  const [date, setDate] = useState<DateRange | undefined>(last7Days)

  return (
    <div>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className="w-[300px] justify-start text-left font-normal"
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {/* Show selected range or placeholder */}
            {date?.from ? (
              date.to ? (
                <>{format(date.from, "LLL dd, y")} - {format(date.to, "LLL dd, y")}</>
              ) : (
                format(date.from, "LLL dd, y")
              )
            ) : (
              <span>Pick a date range</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto mr-6 flex p-0" align="start">
          {/* Presets Sidebar */}
          <div className="flex flex-col space-y-1 border-r p-3 min-w-[140px]">
            <div className="text-xs font-semibold text-muted-foreground mb-2 px-2">
              Quick Select
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8"
              onClick={() => {
                setDate({
                  from: today,
                  to: today,
                })
              }}
            >
              Today
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8"
              onClick={() => {
                setDate(yesterday)
              }}
            >
              Yesterday
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8"
              onClick={() => {
                setDate(last7Days)
              }}
            >
              Last 7 days
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8"
              onClick={() => {
                setDate(last30Days)
              }}
            >
              Last 30 days
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8"
              onClick={() => {
                setDate(monthToDate)
              }}
            >
              Month to date
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8"
              onClick={() => {
                setDate(lastMonth)
              }}
            >
              Last month
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8"
              onClick={() => {
                setDate(yearToDate)
              }}
            >
              Year to date
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8"
              onClick={() => {
                setDate(lastYear)
              }}
            >
              Last year
            </Button>
          </div>
          {/* Calendar */}
          <div className="p-3">
            <Calendar
              mode="range"
              selected={date}
              onSelect={(newDate) => {
                if (newDate) {
                  setDate(newDate)
                }
              }}
              disabled={[{ after: today }]}
              captionLayout="dropdown"
              startMonth={new Date(today.getFullYear() - 10, 0)}
              endMonth={new Date(today.getFullYear(), 11)}
            />
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}