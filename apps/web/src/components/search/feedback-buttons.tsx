'use client';

import { ThumbsUp, ThumbsDown, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSubmitFeedback } from '@/hooks/use-searches';
import type { FeedbackLabel } from '@/lib/types';
import { cn } from '@/lib/utils';
import { useState } from 'react';

interface FeedbackButtonsProps {
  resultId: string;
  searchId?: string;
  candidateVideoId?: string;
  currentFeedback?: FeedbackLabel;
}

export function FeedbackButtons({
  resultId,
  searchId,
  candidateVideoId,
  currentFeedback,
}: FeedbackButtonsProps) {
  const submitFeedback = useSubmitFeedback();
  const [selected, setSelected] = useState<FeedbackLabel | undefined>(currentFeedback);

  const handleFeedback = (label: FeedbackLabel) => {
    setSelected(label);
    submitFeedback.mutate({
      resultId,
      data: {
        label,
        search_id: searchId || '',
        candidate_video_id: candidateVideoId || '',
      },
    });
  };

  return (
    <div className="flex gap-1">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleFeedback('very_relevant')}
        disabled={submitFeedback.isPending}
        className={cn(
          'h-8 px-2',
          selected === 'very_relevant' && 'bg-green-100 text-green-700'
        )}
        title="Very Relevant"
      >
        <ThumbsUp className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleFeedback('somewhat_relevant')}
        disabled={submitFeedback.isPending}
        className={cn(
          'h-8 px-2',
          selected === 'somewhat_relevant' && 'bg-yellow-100 text-yellow-700'
        )}
        title="Somewhat Relevant"
      >
        <Minus className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleFeedback('irrelevant')}
        disabled={submitFeedback.isPending}
        className={cn(
          'h-8 px-2',
          selected === 'irrelevant' && 'bg-red-100 text-red-700'
        )}
        title="Irrelevant"
      >
        <ThumbsDown className="h-4 w-4" />
      </Button>
    </div>
  );
}
