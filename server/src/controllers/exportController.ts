import { Request, Response } from 'express';
import prisma from '../lib/prisma';
import { blocksToCSV, outputsToCSV } from '../services/exportService';

export async function exportBlocksCSV(_req: Request, res: Response) {
  try {
    const blocks = await prisma.copyBlock.findMany({
      include: { project: true, vertical: true },
      orderBy: { createdAt: 'desc' },
    });

    const rows = blocks.map((b) => ({
      id: b.id,
      project: b.project.name,
      vertical: b.vertical.name,
      type: b.type,
      label: b.label,
      content: b.content,
      tone: b.tone || '',
      audience: b.audience || '',
      isApproved: b.isApproved ? 'Yes' : 'No',
    }));

    const csv = blocksToCSV(rows);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=blocks.csv');
    res.send(csv);
  } catch (error) {
    console.error('Error exporting blocks:', error);
    res.status(500).json({ error: 'Failed to export blocks' });
  }
}

export async function exportOutputsCSV(_req: Request, res: Response) {
  try {
    const outputs = await prisma.generatedOutput.findMany({
      include: { project: true, vertical: true },
      orderBy: { createdAt: 'desc' },
    });

    const rows = await Promise.all(
      outputs.map(async (o) => {
        const [hook, problem, discovery, benefit, cta] = await Promise.all([
          o.hookBlockId ? prisma.copyBlock.findUnique({ where: { id: o.hookBlockId } }) : null,
          o.problemBlockId ? prisma.copyBlock.findUnique({ where: { id: o.problemBlockId } }) : null,
          o.discoveryBlockId ? prisma.copyBlock.findUnique({ where: { id: o.discoveryBlockId } }) : null,
          o.benefitBlockId ? prisma.copyBlock.findUnique({ where: { id: o.benefitBlockId } }) : null,
          o.ctaBlockId ? prisma.copyBlock.findUnique({ where: { id: o.ctaBlockId } }) : null,
        ]);

        return {
          id: o.id,
          project: o.project.name,
          vertical: o.vertical.name,
          output_type: o.outputType,
          hook_label: hook?.label || '',
          hook_text: hook?.content || '',
          problem_label: problem?.label || '',
          problem_text: problem?.content || '',
          discovery_label: discovery?.label || '',
          discovery_text: discovery?.content || '',
          benefit_label: benefit?.label || '',
          benefit_text: benefit?.content || '',
          cta_label: cta?.label || '',
          cta_text: cta?.content || '',
          full_text: o.fullText,
          status: o.status,
        };
      })
    );

    const csv = outputsToCSV(rows);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=outputs.csv');
    res.send(csv);
  } catch (error) {
    console.error('Error exporting outputs:', error);
    res.status(500).json({ error: 'Failed to export outputs' });
  }
}

export async function exportOutputsJSON(_req: Request, res: Response) {
  try {
    const outputs = await prisma.generatedOutput.findMany({
      include: { project: true, vertical: true },
      orderBy: { createdAt: 'desc' },
    });

    const enriched = await Promise.all(
      outputs.map(async (o) => {
        const [hook, problem, discovery, benefit, cta] = await Promise.all([
          o.hookBlockId ? prisma.copyBlock.findUnique({ where: { id: o.hookBlockId } }) : null,
          o.problemBlockId ? prisma.copyBlock.findUnique({ where: { id: o.problemBlockId } }) : null,
          o.discoveryBlockId ? prisma.copyBlock.findUnique({ where: { id: o.discoveryBlockId } }) : null,
          o.benefitBlockId ? prisma.copyBlock.findUnique({ where: { id: o.benefitBlockId } }) : null,
          o.ctaBlockId ? prisma.copyBlock.findUnique({ where: { id: o.ctaBlockId } }) : null,
        ]);

        return {
          ...o,
          hookBlock: hook,
          problemBlock: problem,
          discoveryBlock: discovery,
          benefitBlock: benefit,
          ctaBlock: cta,
        };
      })
    );

    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', 'attachment; filename=outputs.json');
    res.json(enriched);
  } catch (error) {
    console.error('Error exporting outputs JSON:', error);
    res.status(500).json({ error: 'Failed to export outputs' });
  }
}
