'use client';

import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { getHealth } from '@/lib/api';

export default function SettingsPage() {
  const { data: health, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Application configuration and status
        </p>
      </div>

      {/* App Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Application</CardTitle>
          <CardDescription>Content Finder web application</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Version</span>
            <span className="font-medium">0.1.0</span>
          </div>
          <Separator />
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Framework</span>
            <span className="font-medium">Next.js 15</span>
          </div>
          <Separator />
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Runtime</span>
            <span className="font-medium">React 19</span>
          </div>
        </CardContent>
      </Card>

      {/* API Health */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">API Status</CardTitle>
          <CardDescription>Backend service health check</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : error ? (
              <div className="flex items-center gap-2">
                <XCircle className="h-4 w-4 text-destructive" />
                <Badge variant="destructive">Unreachable</Badge>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <Badge className="bg-green-100 text-green-800">
                  {health?.status ?? 'Healthy'}
                </Badge>
              </div>
            )}
          </div>
          {health && (
            <>
              <Separator />
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">API Version</span>
                <span className="font-medium">{health.version}</span>
              </div>
              {health.uptime !== undefined && (
                <>
                  <Separator />
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Uptime</span>
                    <span className="font-medium">
                      {Math.floor(health.uptime / 3600)}h{' '}
                      {Math.floor((health.uptime % 3600) / 60)}m
                    </span>
                  </div>
                </>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Configuration</CardTitle>
          <CardDescription>Current environment settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">API Endpoint</span>
            <span className="font-mono text-xs">
              {process.env.NEXT_PUBLIC_API_URL || '/api (proxy)'}
            </span>
          </div>
          <Separator />
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Output Mode</span>
            <span className="font-medium">Standalone</span>
          </div>
        </CardContent>
      </Card>

      {/* Compliance */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Compliance</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This application is designed for content discovery and analysis
            purposes. All video content is processed in accordance with
            platform terms of service and applicable data protection
            regulations. No personal data is stored beyond what is necessary
            for search and analysis functionality. Users are responsible for
            ensuring compliance with local regulations when using discovered
            content.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
