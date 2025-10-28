// frontend/src/app/(protected)/ProtectedClientLayout.tsx
'use client'; // <-- THIS IS THE CRITICAL FIX

import { LeftSidebar } from "@/components/custom/LeftSidebar";
import { RightSidebarSheet } from "@/components/custom/RightSidebarSheet";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { buttonVariants } from "@/components/ui/button";
import { Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import React from "react";

export function ProtectedClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <LeftSidebar />
        <div className="flex flex-1 flex-col">
          <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-6">
            <SidebarTrigger className={cn(buttonVariants({ variant: "outline", size: "icon" }))}>
              <Menu className="h-4 w-4" />
              <span className="sr-only">Toggle Sidebar</span>
            </SidebarTrigger>
            <div className="flex-1"></div>
            <RightSidebarSheet />
          </header>
          <main className="flex-1 overflow-y-auto p-8">
            {children}
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}