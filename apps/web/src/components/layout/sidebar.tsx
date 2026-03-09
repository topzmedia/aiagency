'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Search,
  FolderOpen,
  Upload,
  Settings,
  Video,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/searches', label: 'Searches', icon: Search },
  { href: '/collections', label: 'Collections', icon: FolderOpen },
  { href: '/ingestion', label: 'Ingestion', icon: Upload },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 z-30">
      <div className="flex flex-col flex-grow border-r bg-card pt-5 overflow-y-auto">
        <div className="flex items-center gap-2 px-6 pb-6">
          <Video className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold">Content Finder</span>
        </div>

        <nav className="flex-1 px-3 space-y-1">
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

        <div className="p-4 border-t">
          <p className="text-xs text-muted-foreground">Content Finder v0.1.0</p>
        </div>
      </div>
    </aside>
  );
}
