export interface Vertical {
  id: string;
  name: string;
  slug: string;
  createdAt: string;
  updatedAt: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  verticalId: string;
  vertical: Vertical;
  createdAt: string;
  updatedAt: string;
  _count?: { blocks: number; outputs: number };
}

export interface CopyBlock {
  id: string;
  projectId: string;
  verticalId: string;
  type: BlockType;
  label: string;
  content: string;
  tone?: string;
  audience?: string;
  angle?: string;
  isApproved: boolean;
  createdAt: string;
  updatedAt: string;
  project?: Project;
  vertical?: Vertical;
}

export interface GeneratedOutput {
  id: string;
  projectId: string;
  verticalId: string;
  outputType: OutputType;
  hookBlockId?: string;
  problemBlockId?: string;
  discoveryBlockId?: string;
  benefitBlockId?: string;
  ctaBlockId?: string;
  fullText: string;
  combinationHash: string;
  status: OutputStatus;
  notes?: string;
  createdAt: string;
  updatedAt: string;
  project?: Project;
  vertical?: Vertical;
  hookBlock?: CopyBlock;
  problemBlock?: CopyBlock;
  discoveryBlock?: CopyBlock;
  benefitBlock?: CopyBlock;
  ctaBlock?: CopyBlock;
}

export interface CompositionTemplate {
  id: string;
  name: string;
  description: string;
  slots: string[];
  template: string;
}

export type BlockType = 'HOOK' | 'PROBLEM' | 'DISCOVERY' | 'BENEFIT' | 'CTA';
export type OutputType = 'AD_COPY' | 'VIDEO_SCRIPT';
export type OutputStatus = 'DRAFT' | 'APPROVED' | 'ARCHIVED';

export const BLOCK_TYPES: BlockType[] = ['HOOK', 'PROBLEM', 'DISCOVERY', 'BENEFIT', 'CTA'];
export const OUTPUT_TYPES: OutputType[] = ['AD_COPY', 'VIDEO_SCRIPT'];
export const OUTPUT_STATUSES: OutputStatus[] = ['DRAFT', 'APPROVED', 'ARCHIVED'];
