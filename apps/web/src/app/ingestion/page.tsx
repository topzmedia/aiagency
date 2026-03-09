'use client';

import { useState } from 'react';
import {
  Upload,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { useIngestionJobs, useCreateIngestionJob } from '@/hooks/use-ingestion';
import type { IngestionSourceType } from '@/lib/types';
import { formatDistanceToNow } from 'date-fns';

const statusIcons: Record<string, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-yellow-500" />,
  running: <Play className="h-4 w-4 text-blue-500" />,
  completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-red-500" />,
};

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function IngestionPage() {
  const { data: jobs, isLoading } = useIngestionJobs();
  const createJob = useCreateIngestionJob();

  const [sourceType, setSourceType] = useState<IngestionSourceType>('demo_seed');
  const [folderPath, setFolderPath] = useState('');
  const [csvData, setCsvData] = useState('');
  const [urls, setUrls] = useState('');
  const [seedCount, setSeedCount] = useState('10');
  const [error, setError] = useState('');

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    let config: Record<string, unknown> = {};

    switch (sourceType) {
      case 'local_folder':
        if (!folderPath.trim()) {
          setError('Folder path is required');
          return;
        }
        config = { path: folderPath.trim() };
        break;
      case 'csv_import':
        if (!csvData.trim()) {
          setError('CSV data is required');
          return;
        }
        config = { csv_data: csvData.trim() };
        break;
      case 'url_stub':
        if (!urls.trim()) {
          setError('URLs are required');
          return;
        }
        config = { urls: urls.split('\n').filter(Boolean) };
        break;
      case 'demo_seed':
        config = { count: parseInt(seedCount) || 10 };
        break;
    }

    try {
      await createJob.mutateAsync({ source_type: sourceType, config });
      setFolderPath('');
      setCsvData('');
      setUrls('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create job');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Ingestion</h1>
        <p className="text-muted-foreground mt-1">
          Import video content for analysis and searching
        </p>
      </div>

      {/* Create Job Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">New Ingestion Job</CardTitle>
          <CardDescription>Import videos from various sources</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-4">
            {error && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="sourceType">Source Type</Label>
              <Select
                id="sourceType"
                value={sourceType}
                onChange={(e) =>
                  setSourceType(e.target.value as IngestionSourceType)
                }
              >
                <option value="demo_seed">Demo Seed Data</option>
                <option value="local_folder">Local Folder</option>
                <option value="csv_import">CSV Import</option>
                <option value="url_stub">URL List</option>
              </Select>
            </div>

            {sourceType === 'local_folder' && (
              <div className="space-y-2">
                <Label htmlFor="folderPath">Folder Path</Label>
                <Input
                  id="folderPath"
                  placeholder="/path/to/videos"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                />
              </div>
            )}

            {sourceType === 'csv_import' && (
              <div className="space-y-2">
                <Label htmlFor="csvData">CSV Data</Label>
                <Textarea
                  id="csvData"
                  placeholder="url,platform,caption&#10;https://...,tiktok,My video"
                  value={csvData}
                  onChange={(e) => setCsvData(e.target.value)}
                  rows={6}
                />
              </div>
            )}

            {sourceType === 'url_stub' && (
              <div className="space-y-2">
                <Label htmlFor="urls">URLs (one per line)</Label>
                <Textarea
                  id="urls"
                  placeholder="https://tiktok.com/...&#10;https://youtube.com/..."
                  value={urls}
                  onChange={(e) => setUrls(e.target.value)}
                  rows={6}
                />
              </div>
            )}

            {sourceType === 'demo_seed' && (
              <div className="space-y-2">
                <Label htmlFor="seedCount">Number of seed videos</Label>
                <Input
                  id="seedCount"
                  type="number"
                  min="1"
                  max="1000"
                  value={seedCount}
                  onChange={(e) => setSeedCount(e.target.value)}
                />
              </div>
            )}

            <Button type="submit" disabled={createJob.isPending}>
              {createJob.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Start Ingestion
            </Button>
          </form>
        </CardContent>
      </Card>

      <Separator />

      {/* Jobs List */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Ingestion Jobs</h2>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : !jobs || jobs.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Upload className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No ingestion jobs yet. Create one above.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <Card key={job.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        {statusIcons[job.status]}
                        <span className="font-medium text-sm">
                          {job.source_type.replace('_', ' ').toUpperCase()}
                        </span>
                        <Badge
                          className={statusColors[job.status] ?? ''}
                          variant="secondary"
                        >
                          {job.status}
                        </Badge>
                      </div>

                      {(job.status === 'running' || job.status === 'pending') && (
                        <div className="flex items-center gap-3">
                          <Progress
                            value={job.progress * 100}
                            className="flex-1 h-2"
                          />
                          <span className="text-sm text-muted-foreground">
                            {Math.round(job.progress * 100)}%
                          </span>
                        </div>
                      )}

                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>Total: {job.total_items}</span>
                        <span>Processed: {job.processed_items}</span>
                        {job.failed_items > 0 && (
                          <span className="text-destructive">
                            Failed: {job.failed_items}
                          </span>
                        )}
                        <span>
                          {formatDistanceToNow(new Date(job.created_at), {
                            addSuffix: true,
                          })}
                        </span>
                      </div>

                      {job.error_message && (
                        <p className="text-sm text-destructive bg-destructive/10 p-2 rounded">
                          {job.error_message}
                        </p>
                      )}

                      {job.logs.length > 0 && (
                        <details className="text-xs">
                          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                            Logs ({job.logs.length})
                          </summary>
                          <pre className="mt-1 bg-muted p-2 rounded overflow-auto max-h-32 text-xs">
                            {job.logs.join('\n')}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
