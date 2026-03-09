import { Request, Response } from 'express';
import prisma from '../lib/prisma';
import { createProjectSchema, updateProjectSchema } from '../validators';
import { contentBank } from '../data/contentBank';

const BLOCK_TYPES = ['HOOK', 'PROBLEM', 'DISCOVERY', 'BENEFIT', 'CTA'] as const;
const TONES = ['professional', 'casual', 'urgent', 'friendly', 'authoritative'];

export async function getProjects(req: Request, res: Response) {
  try {
    const { verticalId } = req.query;
    const where: any = {};
    if (verticalId) where.verticalId = verticalId;

    const projects = await prisma.project.findMany({
      where,
      include: { vertical: true },
      orderBy: { updatedAt: 'desc' },
    });
    res.json(projects);
  } catch (error) {
    console.error('Error fetching projects:', error);
    res.status(500).json({ error: 'Failed to fetch projects' });
  }
}

export async function getProject(req: Request, res: Response) {
  try {
    const project = await prisma.project.findUnique({
      where: { id: req.params.id },
      include: {
        vertical: true,
        _count: { select: { blocks: true, outputs: true } },
      },
    });
    if (!project) return res.status(404).json({ error: 'Project not found' });
    res.json(project);
  } catch (error) {
    console.error('Error fetching project:', error);
    res.status(500).json({ error: 'Failed to fetch project' });
  }
}

export async function createProject(req: Request, res: Response) {
  try {
    const data = createProjectSchema.parse(req.body);
    const project = await prisma.project.create({
      data,
      include: { vertical: true },
    });

    // Auto-populate copy blocks from content bank
    const verticalName = project.vertical?.name;
    const bank = verticalName ? contentBank[verticalName] : null;
    if (bank) {
      const blockData: any[] = [];
      for (const blockType of BLOCK_TYPES) {
        const lines = bank[blockType];
        if (!lines) continue;
        for (let i = 0; i < lines.length; i++) {
          blockData.push({
            type: blockType,
            label: `${blockType.charAt(0) + blockType.slice(1).toLowerCase()} #${i + 1}`,
            content: lines[i],
            tone: TONES[i % TONES.length],
            audience: 'general',
            projectId: project.id,
            verticalId: project.verticalId,
            isApproved: true,
          });
        }
      }
      if (blockData.length > 0) {
        await prisma.copyBlock.createMany({ data: blockData });
      }
    }

    res.status(201).json(project);
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    console.error('Error creating project:', error);
    res.status(500).json({ error: 'Failed to create project' });
  }
}

export async function updateProject(req: Request, res: Response) {
  try {
    const data = updateProjectSchema.parse(req.body);
    const project = await prisma.project.update({
      where: { id: req.params.id },
      data,
      include: { vertical: true },
    });
    res.json(project);
  } catch (error: any) {
    if (error.name === 'ZodError') {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'Project not found' });
    }
    console.error('Error updating project:', error);
    res.status(500).json({ error: 'Failed to update project' });
  }
}

export async function deleteProject(req: Request, res: Response) {
  try {
    await prisma.project.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (error: any) {
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'Project not found' });
    }
    console.error('Error deleting project:', error);
    res.status(500).json({ error: 'Failed to delete project' });
  }
}
