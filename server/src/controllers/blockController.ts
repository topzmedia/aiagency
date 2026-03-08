import { Request, Response } from 'express';
import prisma from '../lib/prisma';
import {
  createBlockSchema,
  updateBlockSchema,
  generateBlocksSchema,
  bulkApproveSchema,
  bulkDeleteSchema,
} from '../validators';
import { generateBlocks } from '../services/blockGenerationService';
import { BlockType } from '../types';

export async function getBlocks(req: Request, res: Response) {
  try {
    const { projectId, verticalId, type, isApproved, search } = req.query;
    const where: any = {};
    if (projectId) where.projectId = projectId;
    if (verticalId) where.verticalId = verticalId;
    if (type) where.type = type;
    if (isApproved === 'true') where.isApproved = true;
    if (search) {
      where.OR = [
        { label: { contains: search as string } },
        { content: { contains: search as string } },
      ];
    }

    const blocks = await prisma.copyBlock.findMany({
      where,
      include: { project: true, vertical: true },
      orderBy: { createdAt: 'desc' },
    });
    res.json(blocks);
  } catch (error) {
    console.error('Error fetching blocks:', error);
    res.status(500).json({ error: 'Failed to fetch blocks' });
  }
}

export async function getBlock(req: Request, res: Response) {
  try {
    const block = await prisma.copyBlock.findUnique({
      where: { id: req.params.id },
      include: { project: true, vertical: true },
    });
    if (!block) return res.status(404).json({ error: 'Block not found' });
    res.json(block);
  } catch (error) {
    console.error('Error fetching block:', error);
    res.status(500).json({ error: 'Failed to fetch block' });
  }
}

export async function createBlock(req: Request, res: Response) {
  try {
    const data = createBlockSchema.parse(req.body);
    const block = await prisma.copyBlock.create({
      data,
      include: { project: true, vertical: true },
    });
    res.status(201).json(block);
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    console.error('Error creating block:', error);
    res.status(500).json({ error: 'Failed to create block' });
  }
}

export async function updateBlock(req: Request, res: Response) {
  try {
    const data = updateBlockSchema.parse(req.body);
    const block = await prisma.copyBlock.update({
      where: { id: req.params.id },
      data,
      include: { project: true, vertical: true },
    });
    res.json(block);
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'Block not found' });
    }
    console.error('Error updating block:', error);
    res.status(500).json({ error: 'Failed to update block' });
  }
}

export async function deleteBlock(req: Request, res: Response) {
  try {
    await prisma.copyBlock.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (error: any) {
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'Block not found' });
    }
    console.error('Error deleting block:', error);
    res.status(500).json({ error: 'Failed to delete block' });
  }
}

export async function generateBlocksHandler(req: Request, res: Response) {
  try {
    const params = generateBlocksSchema.parse(req.body);

    // Verify project and vertical exist
    const [project, vertical] = await Promise.all([
      prisma.project.findUnique({ where: { id: params.projectId } }),
      prisma.vertical.findUnique({ where: { id: params.verticalId } }),
    ]);
    if (!project) return res.status(404).json({ error: 'Project not found' });
    if (!vertical) return res.status(404).json({ error: 'Vertical not found' });

    const totalRequested = params.hooks + params.problems + params.discoveries + params.benefits + params.ctas;
    if (totalRequested === 0) {
      return res.status(400).json({ error: 'Must request at least one block' });
    }

    const blockTypes: { type: BlockType; count: number }[] = [
      { type: 'HOOK', count: params.hooks },
      { type: 'PROBLEM', count: params.problems },
      { type: 'DISCOVERY', count: params.discoveries },
      { type: 'BENEFIT', count: params.benefits },
      { type: 'CTA', count: params.ctas },
    ];

    const allGenerated = [];
    for (const { type, count } of blockTypes) {
      if (count > 0) {
        const blocks = generateBlocks({
          vertical: vertical.name,
          type,
          count,
          tone: params.tone,
          audience: params.audience,
          readingLevel: params.readingLevel,
          maxLength: params.maxLength,
          outputType: params.outputType,
        });
        allGenerated.push(...blocks);
      }
    }

    // Save to DB
    const created = await prisma.$transaction(
      allGenerated.map((block) =>
        prisma.copyBlock.create({
          data: {
            projectId: params.projectId,
            verticalId: params.verticalId,
            type: block.type,
            label: block.label,
            content: block.content,
            tone: block.tone || null,
            audience: block.audience || null,
          },
          include: { project: true, vertical: true },
        })
      )
    );

    res.status(201).json(created);
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    console.error('Error generating blocks:', error);
    res.status(500).json({ error: 'Failed to generate blocks' });
  }
}

export async function bulkApprove(req: Request, res: Response) {
  try {
    const { ids } = bulkApproveSchema.parse(req.body);
    await prisma.copyBlock.updateMany({
      where: { id: { in: ids } },
      data: { isApproved: true },
    });
    res.json({ success: true, count: ids.length });
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    console.error('Error bulk approving:', error);
    res.status(500).json({ error: 'Failed to bulk approve' });
  }
}

export async function bulkDelete(req: Request, res: Response) {
  try {
    const { ids } = bulkDeleteSchema.parse(req.body);
    await prisma.copyBlock.deleteMany({
      where: { id: { in: ids } },
    });
    res.json({ success: true, count: ids.length });
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    console.error('Error bulk deleting:', error);
    res.status(500).json({ error: 'Failed to bulk delete' });
  }
}
