'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Download,
  Loader2,
  LayoutGrid,
  List,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useSearch, useSearchResults } from '@/hooks/use-searches';
import { ResultCard } from '@/components/search/result-card';
import { FeedbackButtons } from '@/components/search/feedback-buttons';
import { getExportUrl } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

const statusColors: Record<string, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function SearchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const { data: search, isLoading, error } = useSearch(id);
  const { data: resultData, isLoading: resultsLoading } = useSearchResults(
    id,
    !!search && search.status === 'completed'
  );

  const results = resultData?.results ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !search) {
    return (
      <div className="text-center py-16">
        <p className="text-destructive">Failed to load search.</p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/searches">Back to Searches</Link>
        </Button>
      </div>
    );
  }

  const isInProgress =
    search.status !== 'completed' && search.status !== 'failed';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/searches">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight truncate">
              {search.raw_query}
            </h1>
            <Badge
              className={statusColors[search.status] ?? ''}
              variant="secondary"
            >
              {search.status}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Created{' '}
            {formatDistanceToNow(new Date(search.created_at), {
              addSuffix: true,
            })}
            {search.platforms && search.platforms.length > 0 &&
              ` / Platforms: ${search.platforms.join(', ')}`}
          </p>
        </div>
      </div>

      {/* Progress */}
      {isInProgress && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <div className="flex-1">
                <p className="text-sm font-medium">
                  {search.status === 'queued'
                    ? 'Waiting to start...'
                    : 'Processing search...'}
                </p>
                <Progress
                  value={search.progress_percent}
                  className="mt-2 h-2"
                />
              </div>
              <span className="text-sm font-medium">
                {search.progress_percent}%
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Candidates Found
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{search.total_candidates}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Analyzed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{search.total_analyzed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{search.total_results}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Threshold
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {(search.confidence_threshold * 100).toFixed(0)}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Actions bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'cards' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('cards')}
          >
            <LayoutGrid className="h-4 w-4 mr-1" />
            Cards
          </Button>
          <Button
            variant={viewMode === 'table' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('table')}
          >
            <List className="h-4 w-4 mr-1" />
            Table
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-1" />
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => window.open(getExportUrl(id, 'csv'), '_blank')}
              >
                Export CSV
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => window.open(getExportUrl(id, 'json'), '_blank')}
              >
                Export JSON
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          {search.status === 'completed' && (
            <Button variant="outline" size="sm" disabled>
              <RefreshCw className="h-4 w-4 mr-1" />
              Rerank
            </Button>
          )}
        </div>
      </div>

      {/* Results */}
      {resultsLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : results.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          {isInProgress ? (
            <p>Results will appear here as the search progresses.</p>
          ) : (
            <p>No results found for this search.</p>
          )}
        </div>
      ) : viewMode === 'cards' ? (
        <div className="space-y-3">
          {results.map((result) => (
            <ResultCard key={result.id} result={result} />
          ))}
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Caption</TableHead>
                <TableHead>Platform</TableHead>
                <TableHead>Creator</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead>Feedback</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((result) => (
                <TableRow key={result.id}>
                  <TableCell className="font-mono text-muted-foreground">
                    {result.rank_position}
                  </TableCell>
                  <TableCell className="max-w-xs truncate">
                    {result.caption_text || 'No caption'}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{result.platform}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {result.creator_handle ? `@${result.creator_handle}` : '-'}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {Math.round(result.final_score * 100)}%
                  </TableCell>
                  <TableCell>
                    <FeedbackButtons resultId={result.id} searchId={id} candidateVideoId={result.candidate_video_id} />
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
