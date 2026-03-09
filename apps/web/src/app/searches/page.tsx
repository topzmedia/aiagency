'use client';

import Link from 'next/link';
import { Plus, Loader2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useSearches } from '@/hooks/use-searches';
import { formatDistanceToNow } from 'date-fns';

const statusColors: Record<string, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function SearchesPage() {
  const { data: searchData, isLoading, error } = useSearches();
  const searches = searchData?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Searches</h1>
          <p className="text-muted-foreground mt-1">
            Manage your video content searches
          </p>
        </div>
        <Button asChild>
          <Link href="/searches/new">
            <Plus className="h-4 w-4 mr-2" />
            New Search
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="text-center py-16 text-destructive">
          <p>Failed to load searches. Please try again.</p>
        </div>
      ) : searches.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No searches yet</p>
          <p className="text-sm mb-4">Create your first search to get started</p>
          <Button asChild>
            <Link href="/searches/new">
              <Plus className="h-4 w-4 mr-2" />
              Create Search
            </Link>
          </Button>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Query</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Platforms</TableHead>
                <TableHead className="text-right">Results</TableHead>
                <TableHead className="text-right">Progress</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {searches.map((search) => (
                <TableRow key={search.id}>
                  <TableCell>
                    <Link
                      href={`/searches/${search.id}`}
                      className="font-medium hover:underline"
                    >
                      {search.raw_query.length > 60
                        ? search.raw_query.slice(0, 60) + '...'
                        : search.raw_query}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge
                      className={statusColors[search.status] ?? ''}
                      variant="secondary"
                    >
                      {search.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      {(search.platforms ?? []).map((p) => (
                        <Badge key={p} variant="outline" className="text-xs">
                          {p}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">{search.total_results}</TableCell>
                  <TableCell className="text-right">{search.progress_percent}%</TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {formatDistanceToNow(new Date(search.created_at), { addSuffix: true })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
