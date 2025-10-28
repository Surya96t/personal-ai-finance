// frontend/src/components/custom/LeftSidebar.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { UserButton } from '@clerk/nextjs';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarHeader,
  SidebarFooter,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from '@/components/ui/sidebar';
import {
  LayoutDashboard,
  ArrowRightLeft,
  Coins,
  Receipt,
  FileText,
  ShieldCheck,
  BarChart3,
  Goal,
} from 'lucide-react';

// Define our navigation links (unchanged)
const navLinks = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/transactions', label: 'Transactions', icon: ArrowRightLeft },
];

const futureLinks = [
    { href: '#', label: 'Accounts', icon: Coins },
    { href: '#', label: 'Reports', icon: BarChart3 },
    { href: '#', label: 'Budgets', icon: Receipt },
    { href: '#', label: 'Goals', icon: Goal },
    { href: '#', label: 'Subscriptions', icon: ShieldCheck },
    { href: '#', label: 'Documents', icon: FileText },
];

export function LeftSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        {/* --- THIS SECTION CONTAINS THE FIX --- */}
        {/* This title is visible by default, but hidden when collapsed */}
        <h1 className="text-2xl font-bold group-data-[collapsible=icon]:hidden">AI Finance</h1>
        
        {/* This abbreviated title is hidden by default, but visible when collapsed */}
        <h1 className="text-2xl font-bold hidden group-data-[collapsible=icon]:block">AF</h1>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          {/* The group label is also hidden when collapsed */}
          <SidebarGroupLabel className="group-data-[collapsible=icon]:hidden">Menu</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navLinks.map((link) => {
                const isActive = pathname.startsWith(link.href);
                return (
                  <SidebarMenuItem key={link.label}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link href={link.href}>
                        <link.icon className="w-4 h-4" />
                        {/* The text label is hidden when collapsed */}
                        <span className="group-data-[collapsible=icon]:hidden">{link.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className="group-data-[collapsible=icon]:hidden">Coming Soon</SidebarGroupLabel>
          <SidebarGroupContent>
             <SidebarMenu>
              {futureLinks.map((link) => (
                <SidebarMenuItem key={link.label}>
                    <SidebarMenuButton className="cursor-not-allowed text-muted-foreground" disabled>
                      <link.icon className="w-4 h-4" />
                      <span className="group-data-[collapsible=icon]:hidden">{link.label}</span>
                    </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <UserButton afterSignOutUrl="/" />
      </SidebarFooter>
    </Sidebar>
  );
}