'use client';

import { Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useResultExplanation } from '@/hooks/use-searches';

interface ResultExplainProps {
  resultId: string;
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const percentage = Math.round(value * 100);
  const color =
    percentage >= 70
      ? 'bg-green-500'
      : percentage >= 40
        ? 'bg-yellow-500'
        : 'bg-red-500';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="font-medium">{percentage}%</span>
      </div>
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export function ResultExplain({ resultId }: ResultExplainProps) {
  const { data: explanation, isLoading, error } = useResultExplanation(resultId, true);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !explanation) {
    return (
      <div className="text-sm text-muted-foreground py-4">
        Unable to load explanation.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Score Breakdown */}
      <div>
        <h4 className="text-sm font-semibold mb-3">Score Breakdown</h4>
        <div className="space-y-2">
          <ScoreBar label="Visual" value={explanation.score_breakdown.visual_score} />
          <ScoreBar label="Audio" value={explanation.score_breakdown.audio_score} />
          <ScoreBar label="Text" value={explanation.score_breakdown.text_score} />
          <ScoreBar label="Metadata" value={explanation.score_breakdown.metadata_score} />
          <Separator />
          <ScoreBar label="Overall" value={explanation.score_breakdown.overall_score} />
        </div>
      </div>

      <Separator />

      {/* Reason Codes */}
      {explanation.reason_codes.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Reason Codes</h4>
          <div className="flex flex-wrap gap-1">
            {explanation.reason_codes.map((code) => (
              <Badge key={code} variant="secondary" className="text-xs">
                {code}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Detected Objects */}
      {explanation.detected_objects.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Detected Objects</h4>
          <div className="flex flex-wrap gap-1">
            {explanation.detected_objects.map((obj) => (
              <Badge key={obj} variant="outline" className="text-xs">
                {obj}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Scene Labels */}
      {explanation.scene_labels.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Scene Labels</h4>
          <div className="flex flex-wrap gap-1">
            {explanation.scene_labels.map((label) => (
              <Badge key={label} variant="outline" className="text-xs">
                {label}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {explanation.actions_detected.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Actions Detected</h4>
          <div className="flex flex-wrap gap-1">
            {explanation.actions_detected.map((action) => (
              <Badge key={action} variant="outline" className="text-xs">
                {action}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* OCR Text */}
      {explanation.ocr_text && (
        <div>
          <h4 className="text-sm font-semibold mb-2">OCR Text</h4>
          <p className="text-sm text-muted-foreground bg-muted p-2 rounded">
            {explanation.ocr_text}
          </p>
        </div>
      )}

      {/* Transcript */}
      {explanation.transcript_excerpt && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Transcript Excerpt</h4>
          <p className="text-sm text-muted-foreground bg-muted p-2 rounded">
            {explanation.transcript_excerpt}
          </p>
        </div>
      )}

      {/* Duplicate Group */}
      {explanation.duplicate_group && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Duplicate Group</h4>
          <Badge variant="secondary">{explanation.duplicate_group}</Badge>
        </div>
      )}

      {/* Matched Segments */}
      {explanation.matched_segments.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Matched Segments</h4>
          <div className="space-y-1">
            {explanation.matched_segments.map((seg, i) => (
              <div
                key={i}
                className="text-xs flex items-center gap-2 bg-muted p-2 rounded"
              >
                <span className="font-mono">
                  {seg.start_time.toFixed(1)}s - {seg.end_time.toFixed(1)}s
                </span>
                <Badge variant="outline" className="text-xs">
                  {seg.label}
                </Badge>
                <span className="text-muted-foreground">
                  {Math.round(seg.confidence * 100)}% conf
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
