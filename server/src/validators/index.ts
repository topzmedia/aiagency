import { z } from 'zod';

export const createProjectSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  verticalId: z.string().min(1, 'Vertical is required'),
});

export const updateProjectSchema = z.object({
  name: z.string().min(1).optional(),
  description: z.string().optional(),
  verticalId: z.string().min(1).optional(),
});

export const createBlockSchema = z.object({
  projectId: z.string().min(1),
  verticalId: z.string().min(1),
  type: z.enum(['HOOK', 'PROBLEM', 'DISCOVERY', 'BENEFIT', 'CTA']),
  label: z.string().min(1),
  content: z.string().min(1),
  tone: z.string().optional(),
  audience: z.string().optional(),
  angle: z.string().optional(),
  isApproved: z.boolean().optional(),
});

export const updateBlockSchema = z.object({
  label: z.string().min(1).optional(),
  content: z.string().min(1).optional(),
  tone: z.string().optional(),
  audience: z.string().optional(),
  angle: z.string().optional(),
  isApproved: z.boolean().optional(),
});

export const generateBlocksSchema = z.object({
  projectId: z.string().min(1, 'Project is required'),
  verticalId: z.string().min(1, 'Vertical is required'),
  outputType: z.enum(['AD_COPY', 'VIDEO_SCRIPT']).default('AD_COPY'),
  hooks: z.number().int().min(0).max(50).default(0),
  problems: z.number().int().min(0).max(50).default(0),
  discoveries: z.number().int().min(0).max(50).default(0),
  benefits: z.number().int().min(0).max(50).default(0),
  ctas: z.number().int().min(0).max(50).default(0),
  tone: z.string().optional(),
  audience: z.string().optional(),
  readingLevel: z.string().optional(),
  maxLength: z.number().int().min(10).optional(),
  customInstructions: z.string().optional(),
});

export const bulkApproveSchema = z.object({
  ids: z.array(z.string().min(1)).min(1),
});

export const bulkDeleteSchema = z.object({
  ids: z.array(z.string().min(1)).min(1),
});

export const composeOutputSchema = z.object({
  projectId: z.string().min(1),
  verticalId: z.string().min(1),
  outputType: z.enum(['AD_COPY', 'VIDEO_SCRIPT']),
  templateId: z.string().min(1),
  hookBlockId: z.string().optional(),
  problemBlockId: z.string().optional(),
  discoveryBlockId: z.string().optional(),
  benefitBlockId: z.string().optional(),
  ctaBlockId: z.string().optional(),
  notes: z.string().optional(),
});

export const bulkGenerateSchema = z.object({
  projectId: z.string().min(1),
  verticalId: z.string().min(1),
  outputType: z.enum(['AD_COPY', 'VIDEO_SCRIPT']),
  templateId: z.string().min(1),
  count: z.number().int().min(1).max(500),
  uniqueOnly: z.boolean().default(true),
  approvedOnly: z.boolean().default(false),
  randomize: z.boolean().default(true),
  lockedHookId: z.string().optional(),
  lockedProblemId: z.string().optional(),
  lockedDiscoveryId: z.string().optional(),
  lockedBenefitId: z.string().optional(),
  lockedCtaId: z.string().optional(),
});

export const updateOutputSchema = z.object({
  status: z.enum(['DRAFT', 'APPROVED', 'ARCHIVED']).optional(),
  notes: z.string().optional(),
});
