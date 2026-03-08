export const BlockType = {
  HOOK: 'HOOK',
  PROBLEM: 'PROBLEM',
  DISCOVERY: 'DISCOVERY',
  BENEFIT: 'BENEFIT',
  CTA: 'CTA',
} as const;
export type BlockType = (typeof BlockType)[keyof typeof BlockType];

export const OutputType = {
  AD_COPY: 'AD_COPY',
  VIDEO_SCRIPT: 'VIDEO_SCRIPT',
} as const;
export type OutputType = (typeof OutputType)[keyof typeof OutputType];

export const OutputStatus = {
  DRAFT: 'DRAFT',
  APPROVED: 'APPROVED',
  ARCHIVED: 'ARCHIVED',
} as const;
export type OutputStatus = (typeof OutputStatus)[keyof typeof OutputStatus];

export const BLOCK_TYPES = [
  BlockType.HOOK,
  BlockType.PROBLEM,
  BlockType.DISCOVERY,
  BlockType.BENEFIT,
  BlockType.CTA,
] as const;
