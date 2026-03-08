import { Request, Response } from 'express';
import prisma from '../lib/prisma';
import { composeOutputSchema, bulkGenerateSchema, updateOutputSchema } from '../validators';
import { composeOutput } from '../services/compositionService';
import {
  generateBulkOutputs,
  computeMaxCombinations,
  createCombinationHash,
} from '../services/bulkGenerationService';

export async function getOutputs(req: Request, res: Response) {
  try {
    const { projectId, verticalId, outputType, status, search } = req.query;
    const where: any = {};
    if (projectId) where.projectId = projectId;
    if (verticalId) where.verticalId = verticalId;
    if (outputType) where.outputType = outputType;
    if (status) where.status = status;
    if (search) {
      where.fullText = { contains: search as string };
    }

    const outputs = await prisma.generatedOutput.findMany({
      where,
      include: { project: true, vertical: true },
      orderBy: { createdAt: 'desc' },
    });

    // Enrich with block data
    const enriched = await Promise.all(
      outputs.map(async (output) => {
        const [hook, problem, discovery, benefit, cta] = await Promise.all([
          output.hookBlockId ? prisma.copyBlock.findUnique({ where: { id: output.hookBlockId } }) : null,
          output.problemBlockId ? prisma.copyBlock.findUnique({ where: { id: output.problemBlockId } }) : null,
          output.discoveryBlockId ? prisma.copyBlock.findUnique({ where: { id: output.discoveryBlockId } }) : null,
          output.benefitBlockId ? prisma.copyBlock.findUnique({ where: { id: output.benefitBlockId } }) : null,
          output.ctaBlockId ? prisma.copyBlock.findUnique({ where: { id: output.ctaBlockId } }) : null,
        ]);
        return { ...output, hookBlock: hook, problemBlock: problem, discoveryBlock: discovery, benefitBlock: benefit, ctaBlock: cta };
      })
    );

    res.json(enriched);
  } catch (error) {
    console.error('Error fetching outputs:', error);
    res.status(500).json({ error: 'Failed to fetch outputs' });
  }
}

export async function getOutput(req: Request, res: Response) {
  try {
    const output = await prisma.generatedOutput.findUnique({
      where: { id: req.params.id },
      include: { project: true, vertical: true },
    });
    if (!output) return res.status(404).json({ error: 'Output not found' });

    const [hook, problem, discovery, benefit, cta] = await Promise.all([
      output.hookBlockId ? prisma.copyBlock.findUnique({ where: { id: output.hookBlockId } }) : null,
      output.problemBlockId ? prisma.copyBlock.findUnique({ where: { id: output.problemBlockId } }) : null,
      output.discoveryBlockId ? prisma.copyBlock.findUnique({ where: { id: output.discoveryBlockId } }) : null,
      output.benefitBlockId ? prisma.copyBlock.findUnique({ where: { id: output.benefitBlockId } }) : null,
      output.ctaBlockId ? prisma.copyBlock.findUnique({ where: { id: output.ctaBlockId } }) : null,
    ]);

    res.json({ ...output, hookBlock: hook, problemBlock: problem, discoveryBlock: discovery, benefitBlock: benefit, ctaBlock: cta });
  } catch (error) {
    console.error('Error fetching output:', error);
    res.status(500).json({ error: 'Failed to fetch output' });
  }
}

export async function composeOutputHandler(req: Request, res: Response) {
  try {
    const data = composeOutputSchema.parse(req.body);

    // Fetch selected blocks
    const blockIds = [data.hookBlockId, data.problemBlockId, data.discoveryBlockId, data.benefitBlockId, data.ctaBlockId].filter(Boolean) as string[];
    const blocks = await prisma.copyBlock.findMany({ where: { id: { in: blockIds } } });
    const blockMap: Record<string, { id: string; content: string }> = {};
    for (const b of blocks) {
      blockMap[b.id] = b;
    }

    const blockContents: Record<string, string> = {};
    if (data.hookBlockId && blockMap[data.hookBlockId]) blockContents.hook = blockMap[data.hookBlockId].content;
    if (data.problemBlockId && blockMap[data.problemBlockId]) blockContents.problem = blockMap[data.problemBlockId].content;
    if (data.discoveryBlockId && blockMap[data.discoveryBlockId]) blockContents.discovery = blockMap[data.discoveryBlockId].content;
    if (data.benefitBlockId && blockMap[data.benefitBlockId]) blockContents.benefit = blockMap[data.benefitBlockId].content;
    if (data.ctaBlockId && blockMap[data.ctaBlockId]) blockContents.cta = blockMap[data.ctaBlockId].content;

    const result = composeOutput({ templateId: data.templateId, blocks: blockContents });

    const hash = createCombinationHash(
      data.templateId,
      data.outputType,
      data.hookBlockId || '',
      data.problemBlockId || '',
      data.discoveryBlockId || '',
      data.benefitBlockId || '',
      data.ctaBlockId || ''
    );

    // Check for existing hash
    const existing = await prisma.generatedOutput.findUnique({ where: { combinationHash: hash } });
    if (existing) {
      return res.status(409).json({ error: 'This exact combination already exists', existingId: existing.id });
    }

    const output = await prisma.generatedOutput.create({
      data: {
        projectId: data.projectId,
        verticalId: data.verticalId,
        outputType: data.outputType,
        hookBlockId: data.hookBlockId || null,
        problemBlockId: data.problemBlockId || null,
        discoveryBlockId: data.discoveryBlockId || null,
        benefitBlockId: data.benefitBlockId || null,
        ctaBlockId: data.ctaBlockId || null,
        fullText: result.fullText,
        combinationHash: hash,
        notes: data.notes || null,
      },
      include: { project: true, vertical: true },
    });

    res.status(201).json({ ...output, ...result });
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    console.error('Error composing output:', error);
    res.status(500).json({ error: 'Failed to compose output' });
  }
}

export async function bulkGenerateHandler(req: Request, res: Response) {
  try {
    const data = bulkGenerateSchema.parse(req.body);

    const where: any = {
      projectId: data.projectId,
      verticalId: data.verticalId,
    };
    if (data.approvedOnly) where.isApproved = true;

    const allBlocks = await prisma.copyBlock.findMany({ where });

    const hooks = allBlocks.filter((b) => b.type === 'HOOK').map((b) => ({ id: b.id, content: b.content, label: b.label }));
    const problems = allBlocks.filter((b) => b.type === 'PROBLEM').map((b) => ({ id: b.id, content: b.content, label: b.label }));
    const discoveries = allBlocks.filter((b) => b.type === 'DISCOVERY').map((b) => ({ id: b.id, content: b.content, label: b.label }));
    const benefits = allBlocks.filter((b) => b.type === 'BENEFIT').map((b) => ({ id: b.id, content: b.content, label: b.label }));
    const ctas = allBlocks.filter((b) => b.type === 'CTA').map((b) => ({ id: b.id, content: b.content, label: b.label }));

    // Get existing hashes if uniqueOnly
    let existingHashes: Set<string> | undefined;
    if (data.uniqueOnly) {
      const existingOutputs = await prisma.generatedOutput.findMany({
        where: { projectId: data.projectId },
        select: { combinationHash: true },
      });
      existingHashes = new Set(existingOutputs.map((o) => o.combinationHash));
    }

    const params = {
      templateId: data.templateId,
      outputType: data.outputType,
      hooks,
      problems,
      discoveries,
      benefits,
      ctas,
      lockedHookId: data.lockedHookId,
      lockedProblemId: data.lockedProblemId,
      lockedDiscoveryId: data.lockedDiscoveryId,
      lockedBenefitId: data.lockedBenefitId,
      lockedCtaId: data.lockedCtaId,
      count: data.count,
      uniqueOnly: data.uniqueOnly,
      randomize: data.randomize,
      existingHashes,
    };

    const maxCombinations = computeMaxCombinations(params);
    const generated = generateBulkOutputs(params);

    // Save to DB
    const created = await prisma.$transaction(
      generated.map((output) =>
        prisma.generatedOutput.create({
          data: {
            projectId: data.projectId,
            verticalId: data.verticalId,
            outputType: data.outputType,
            hookBlockId: output.hookBlockId || null,
            problemBlockId: output.problemBlockId || null,
            discoveryBlockId: output.discoveryBlockId || null,
            benefitBlockId: output.benefitBlockId || null,
            ctaBlockId: output.ctaBlockId || null,
            fullText: output.fullText,
            combinationHash: output.combinationHash,
          },
          include: { project: true, vertical: true },
        })
      )
    );

    res.status(201).json({
      outputs: created,
      generated: created.length,
      maxPossible: maxCombinations,
      warning: data.count > maxCombinations
        ? `Requested ${data.count} but only ${maxCombinations} unique combinations are possible.`
        : undefined,
    });
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    console.error('Error bulk generating:', error);
    res.status(500).json({ error: 'Failed to bulk generate outputs' });
  }
}

export async function updateOutput(req: Request, res: Response) {
  try {
    const data = updateOutputSchema.parse(req.body);
    const output = await prisma.generatedOutput.update({
      where: { id: req.params.id },
      data,
      include: { project: true, vertical: true },
    });
    res.json(output);
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'Output not found' });
    }
    console.error('Error updating output:', error);
    res.status(500).json({ error: 'Failed to update output' });
  }
}

export async function deleteOutput(req: Request, res: Response) {
  try {
    await prisma.generatedOutput.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (error: any) {
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'Output not found' });
    }
    console.error('Error deleting output:', error);
    res.status(500).json({ error: 'Failed to delete output' });
  }
}
