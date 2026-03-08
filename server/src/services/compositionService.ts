import { getTemplateById, renderTemplate } from './templateService';

interface ComposeParams {
  templateId: string;
  blocks: Record<string, string>; // slot name -> content
}

export interface CompositionResult {
  fullText: string;
  charCount: number;
  wordCount: number;
  estimatedSpeakingTime: number; // seconds
}

const WORDS_PER_MINUTE = 150; // average speaking pace

export function composeOutput(params: ComposeParams): CompositionResult {
  const template = getTemplateById(params.templateId);
  if (!template) {
    throw new Error(`Template not found: ${params.templateId}`);
  }

  const fullText = renderTemplate(template, params.blocks);
  const charCount = fullText.length;
  const wordCount = fullText
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
  const estimatedSpeakingTime = Math.ceil((wordCount / WORDS_PER_MINUTE) * 60);

  return {
    fullText,
    charCount,
    wordCount,
    estimatedSpeakingTime,
  };
}

export function calculateMetrics(text: string) {
  const charCount = text.length;
  const wordCount = text
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
  const estimatedSpeakingTime = Math.ceil((wordCount / WORDS_PER_MINUTE) * 60);

  return { charCount, wordCount, estimatedSpeakingTime };
}
