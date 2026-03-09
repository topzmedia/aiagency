'use client';

import { Menu, Video } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Search,
  FolderOpen,
  Upload,
  Settings,
} from 'lucide-react';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/searches', label: 'Searches', icon: Search },
  { href: '/collections', label: 'Collections', icon: FolderOpen },
  { href: '/ingestion', label: 'Ingestion', icon: Upload },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background px-4 md:px-6 md:pl-72">
      {/* Mobile menu */}
      <div className="md:hidden">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0">
            <SheetHeader className="p-6">
              <SheetTitle className="flex items-center gap-2">
                <Video className="h-6 w-6 text-primary" />
                Content Finder
              </SheetTitle>
            </SheetHeader>
            <nav className="px-3 space-y-1">
              {navItems.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== '/' && pathname.startsWith(item.href));
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </SheetContent>
        </Sheet>
      </div>

      <div className="flex-1" />
    </header>
  );
}
