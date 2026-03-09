'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Search, FolderOpen, Video, Plus, ArrowRight, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useSearches, useCreateSearch } from '@/hooks/use-searches';
import { useCollections } from '@/hooks/use-collections';
import { formatDistanceToNow } from 'date-fns';

const statusColors: Record<string, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function DashboardPage() {
  const router = useRouter();
  const [quickQuery, setQuickQuery] = useState('');
  const { data: searchData, isLoading: searchesLoading } = useSearches();
  const { data: collections, isLoading: collectionsLoading } = useCollections();
  const createSearch = useCreateSearch();

  const searches = searchData?.items ?? [];
  const totalSearches = searchData?.total ?? 0;
  const totalResults = searches.reduce((sum, s) => sum + (s.total_results ?? 0), 0);
  const totalCollections = collections?.length ?? 0;

  const recentSearches = searches.slice(0, 5);

  const handleQuickSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickQuery.trim()) return;

    try {
      const search = await createSearch.mutateAsync({ raw_query: quickQuery });
      router.push(`/searches/${search.id}`);
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Welcome to Content Finder. Search and discover video content across platforms.
        </p>
      </div>

      {/* Quick Search */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Quick Search</CardTitle>
          <CardDescription>Enter keywords to find relevant video content</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleQuickSearch} className="flex gap-2">
            <Input
              placeholder="e.g. car crashes, luxury kitchens, dogs playing in snow..."
              value={quickQuery}
              onChange={(e) => setQuickQuery(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={createSearch.isPending || !quickQuery.trim()}>
              {createSearch.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Search className="h-4 w-4 mr-2" />
              )}
              Search
            </Button>
            <Button variant="outline" asChild>
              <Link href="/searches/new">
                <Plus className="h-4 w-4 mr-2" />
                Advanced
              </Link>
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Searches</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {searchesLoading ? '...' : totalSearches}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Results Found</CardTitle>
            <Video className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {searchesLoading ? '...' : totalResults}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collections</CardTitle>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {collectionsLoading ? '...' : totalCollections}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Searches */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">Recent Searches</CardTitle>
            <CardDescription>Your latest content searches</CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/searches">
              View all <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {searchesLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : recentSearches.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No searches yet. Start by creating one above.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentSearches.map((search) => (
                <Link
                  key={search.id}
                  href={`/searches/${search.id}`}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{search.raw_query}</p>
                    <p className="text-xs text-muted-foreground">
                      {search.total_results} results
                      {' / '}
                      {formatDistanceToNow(new Date(search.created_at), { addSuffix: true })}
                    </p>
                  </div>
                  <Badge
                    className={statusColors[search.status] ?? ''}
                    variant="secondary"
                  >
                    {search.status}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
