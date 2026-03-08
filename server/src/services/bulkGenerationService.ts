import crypto from 'crypto';
import { getTemplateById, renderTemplate } from './templateService';

interface BlockSelection {
  id: string;
  content: string;
  label: string;
}

interface BulkGenerationParams {
  templateId: string;
  outputType: string;
  hooks: BlockSelection[];
  problems: BlockSelection[];
  discoveries: BlockSelection[];
  benefits: BlockSelection[];
  ctas: BlockSelection[];
  lockedHookId?: string;
  lockedProblemId?: string;
  lockedDiscoveryId?: string;
  lockedBenefitId?: string;
  lockedCtaId?: string;
  count: number;
  uniqueOnly: boolean;
  randomize: boolean;
  existingHashes?: Set<string>;
}

export interface BulkOutput {
  hookBlockId: string;
  problemBlockId: string;
  discoveryBlockId: string;
  benefitBlockId: string;
  ctaBlockId: string;
  fullText: string;
  combinationHash: string;
}

export function createCombinationHash(
  templateId: string,
  outputType: string,
  hookId: string,
  problemId: string,
  discoveryId: string,
  benefitId: string,
  ctaId: string
): string {
  const input = `${templateId}:${outputType}:${hookId}:${problemId}:${discoveryId}:${benefitId}:${ctaId}`;
  return crypto.createHash('sha256').update(input).digest('hex').substring(0, 16);
}

export function computeMaxCombinations(params: BulkGenerationParams): number {
  const template = getTemplateById(params.templateId);
  if (!template) return 0;

  const slots = template.slots;
  let max = 1;

  if (slots.includes('hook')) {
    max *= params.lockedHookId ? 1 : params.hooks.length;
  }
  if (slots.includes('problem')) {
    max *= params.lockedProblemId ? 1 : params.problems.length;
  }
  if (slots.includes('discovery')) {
    max *= params.lockedDiscoveryId ? 1 : params.discoveries.length;
  }
  if (slots.includes('benefit')) {
    max *= params.lockedBenefitId ? 1 : params.benefits.length;
  }
  if (slots.includes('cta')) {
    max *= params.lockedCtaId ? 1 : params.ctas.length;
  }

  return max;
}

function shuffleArray<T>(arr: T[]): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

function getPool(
  items: BlockSelection[],
  lockedId: string | undefined
): BlockSelection[] {
  if (lockedId) {
    const locked = items.find((i) => i.id === lockedId);
    return locked ? [locked] : items;
  }
  return items;
}

export function generateBulkOutputs(params: BulkGenerationParams): BulkOutput[] {
  const template = getTemplateById(params.templateId);
  if (!template) throw new Error(`Template not found: ${params.templateId}`);

  const slots = template.slots;
  const hookPool = slots.includes('hook') ? getPool(params.hooks, params.lockedHookId) : [{ id: '', content: '', label: '' }];
  const problemPool = slots.includes('problem') ? getPool(params.problems, params.lockedProblemId) : [{ id: '', content: '', label: '' }];
  const discoveryPool = slots.includes('discovery') ? getPool(params.discoveries, params.lockedDiscoveryId) : [{ id: '', content: '', label: '' }];
  const benefitPool = slots.includes('benefit') ? getPool(params.benefits, params.lockedBenefitId) : [{ id: '', content: '', label: '' }];
  const ctaPool = slots.includes('cta') ? getPool(params.ctas, params.lockedCtaId) : [{ id: '', content: '', label: '' }];

  // Generate all possible combinations
  const allCombinations: BulkOutput[] = [];
  const seenHashes = new Set(params.existingHashes || []);

  for (const hook of hookPool) {
    for (const problem of problemPool) {
      for (const discovery of discoveryPool) {
        for (const benefit of benefitPool) {
          for (const cta of ctaPool) {
            const hash = createCombinationHash(
              params.templateId,
              params.outputType,
              hook.id,
              problem.id,
              discovery.id,
              benefit.id,
              cta.id
            );

            if (params.uniqueOnly && seenHashes.has(hash)) {
              continue;
            }

            const blockContents: Record<string, string> = {};
            if (slots.includes('hook')) blockContents.hook = hook.content;
            if (slots.includes('problem')) blockContents.problem = problem.content;
            if (slots.includes('discovery')) blockContents.discovery = discovery.content;
            if (slots.includes('benefit')) blockContents.benefit = benefit.content;
            if (slots.includes('cta')) blockContents.cta = cta.content;

            const fullText = renderTemplate(template, blockContents);

            allCombinations.push({
              hookBlockId: hook.id,
              problemBlockId: problem.id,
              discoveryBlockId: discovery.id,
              benefitBlockId: benefit.id,
              ctaBlockId: cta.id,
              fullText,
              combinationHash: hash,
            });
            seenHashes.add(hash);
          }
        }
      }
    }
  }

  let results = params.randomize ? shuffleArray(allCombinations) : allCombinations;
  return results.slice(0, params.count);
}
