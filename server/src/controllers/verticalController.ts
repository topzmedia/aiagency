import { Request, Response } from 'express';
import prisma from '../lib/prisma';

export async function getVerticals(_req: Request, res: Response) {
  try {
    const verticals = await prisma.vertical.findMany({
      orderBy: { name: 'asc' },
    });
    res.json(verticals);
  } catch (error) {
    console.error('Error fetching verticals:', error);
    res.status(500).json({ error: 'Failed to fetch verticals' });
  }
}
