'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ResultExplain } from './result-explain';
import type { SearchResult } from '@/lib/types';

const platformColors: Record<string, string> = {
  tiktok: 'bg-black text-white',
  instagram: 'bg-gradient-to-r from-purple-500 to-pink-500 text-white',
  youtube: 'bg-red-600 text-white',
  twitter: 'bg-sky-500 text-white',
  other: 'bg-gray-500 text-white',
};

interface ResultCardProps {
  result: SearchResult;
}

export function ResultCard({ result }: ResultCardProps) {
  const [expanded, setExpanded] = useState(false);
  const scorePercent = Math.round(result.final_score * 100);
  const scoreColor =
    scorePercent >= 70
      ? 'bg-green-500'
      : scorePercent >= 40
        ? 'bg-yellow-500'
        : 'bg-red-500';

  const platform = result.platform || 'other';
  const reasonCodes = result.reason_codes_json ?? [];
  const matchedSegments = result.matched_segments_json ?? [];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex gap-4">
          {/* Thumbnail placeholder */}
          <div
            className={`w-24 h-24 rounded-md flex items-center justify-center text-xs font-bold shrink-0 ${
              platformColors[platform] ?? platformColors.other
            }`}
          >
            {platform.toUpperCase()}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium leading-tight line-clamp-2">
                  {result.caption_text || 'No caption available'}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge
                    className={`text-xs ${platformColors[platform] ?? ''}`}
                  >
                    {platform}
                  </Badge>
                  {result.creator_handle && (
                    <span className="text-xs text-muted-foreground">
                      @{result.creator_handle}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {result.source_url && (
                  <Button variant="ghost" size="sm" asChild className="h-8 px-2">
                    <a href={result.source_url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </Button>
                )}
              </div>
            </div>

            {/* Score bar */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium w-10">{scorePercent}%</span>
              <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${scoreColor}`}
                  style={{ width: `${scorePercent}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground">#{result.rank_position}</span>
            </div>

            {/* Reason code chips */}
            <div className="flex flex-wrap gap-1">
              {reasonCodes.map((code) => (
                <Badge key={code} variant="secondary" className="text-xs">
                  {code}
                </Badge>
              ))}
              {matchedSegments.slice(0, 3).map((seg, i) => (
                <Badge key={i} variant="outline" className="text-xs font-mono">
                  {seg.start_sec?.toFixed(1)}s-{seg.end_sec?.toFixed(1)}s
                </Badge>
              ))}
            </div>

            {/* Expand */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="h-7 px-2 text-xs"
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" /> Less details
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" /> More details
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Expanded explanation */}
        {expanded && (
          <div className="mt-4 pt-4 border-t">
            <ResultExplain resultId={result.id} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
