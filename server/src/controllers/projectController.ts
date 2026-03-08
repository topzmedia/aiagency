import { Request, Response } from 'express';
import prisma from '../lib/prisma';
import { createProjectSchema, updateProjectSchema } from '../validators';

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
