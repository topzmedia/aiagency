import { PrismaClient } from '@prisma/client';
import crypto from 'crypto';
import { contentBank } from '../server/src/data/contentBank';

const prisma = new PrismaClient();

function createHash(...parts: string[]): string {
  return crypto.createHash('sha256').update(parts.join(':')).digest('hex').substring(0, 16);
}

const BLOCK_TYPES = ['HOOK', 'PROBLEM', 'DISCOVERY', 'BENEFIT', 'CTA'] as const;
const TONES = ['professional', 'casual', 'urgent', 'friendly', 'authoritative'];

async function main() {
  console.log('Seeding database...');

  // Clear existing data
  await prisma.generatedOutput.deleteMany();
  await prisma.copyBlock.deleteMany();
  await prisma.project.deleteMany();
  await prisma.vertical.deleteMany();

  // Create verticals
  const verticals = [
    { name: 'Home Insurance', slug: 'home-insurance' },
    { name: 'Auto Insurance', slug: 'auto-insurance' },
    { name: 'Roofing', slug: 'roofing' },
    { name: 'Home Windows Replacement', slug: 'home-windows-replacement' },
    { name: 'Home Warranty', slug: 'home-warranty' },
    { name: 'HELOC', slug: 'heloc' },
    { name: 'Mortgage Refinance', slug: 'mortgage-refinance' },
    { name: 'Debt Relief', slug: 'debt-relief' },
  ];

  const createdVerticals = [];
  for (const v of verticals) {
    const vertical = await prisma.vertical.upsert({
      where: { slug: v.slug },
      update: {},
      create: v,
    });
    createdVerticals.push(vertical);
  }

  // Create a project for each vertical
  const projects = [];
  for (const vertical of createdVerticals) {
    const project = await prisma.project.create({
      data: {
        name: `${vertical.name} Campaign`,
        description: `Primary campaign for ${vertical.name} vertical`,
        verticalId: vertical.id,
      },
    });
    projects.push(project);
  }

  // Seed blocks from the content bank for all verticals
  let totalBlocks = 0;
  for (let vi = 0; vi < createdVerticals.length; vi++) {
    const vertical = createdVerticals[vi];
    const project = projects[vi];
    const bank = contentBank[vertical.name];

    if (!bank) {
      console.log(`  Skipping ${vertical.name} — no content bank entry`);
      continue;
    }

    let verticalBlockCount = 0;
    for (const blockType of BLOCK_TYPES) {
      const lines = bank[blockType];
      if (!lines) continue;

      for (let i = 0; i < lines.length; i++) {
        const tone = TONES[i % TONES.length];
        await prisma.copyBlock.create({
          data: {
            type: blockType,
            label: `${blockType.charAt(0) + blockType.slice(1).toLowerCase()} #${i + 1}`,
            content: lines[i],
            tone,
            audience: 'general',
            projectId: project.id,
            verticalId: vertical.id,
            isApproved: true,
          },
        });
        verticalBlockCount++;
      }
    }

    totalBlocks += verticalBlockCount;
    console.log(`  ${vertical.name}: ${verticalBlockCount} blocks seeded`);
  }

  // Create sample outputs for Auto Insurance
  const autoInsurance = createdVerticals.find((v) => v.slug === 'auto-insurance')!;
  const autoProject = projects.find((p) => p.verticalId === autoInsurance.id)!;

  const autoBlocks = await prisma.copyBlock.findMany({
    where: { verticalId: autoInsurance.id },
    orderBy: { id: 'asc' },
  });

  const hook1 = autoBlocks.find((b) => b.type === 'HOOK' && b.label === 'Hook #1');
  const problem1 = autoBlocks.find((b) => b.type === 'PROBLEM' && b.label === 'Problem #1');
  const discovery1 = autoBlocks.find((b) => b.type === 'DISCOVERY' && b.label === 'Discovery #1');
  const benefit1 = autoBlocks.find((b) => b.type === 'BENEFIT' && b.label === 'Benefit #1');
  const cta1 = autoBlocks.find((b) => b.type === 'CTA' && b.label === 'Cta #1');

  if (hook1 && problem1 && discovery1 && benefit1 && cta1) {
    const fullText = `${hook1.content}\n\n${problem1.content}\n\n${discovery1.content}\n\n${benefit1.content}\n\n${cta1.content}`;
    const hash = createHash('default', 'AD_COPY', hook1.id, problem1.id, discovery1.id, benefit1.id, cta1.id);

    await prisma.generatedOutput.create({
      data: {
        projectId: autoProject.id,
        verticalId: autoInsurance.id,
        outputType: 'AD_COPY',
        hookBlockId: hook1.id,
        problemBlockId: problem1.id,
        discoveryBlockId: discovery1.id,
        benefitBlockId: benefit1.id,
        ctaBlockId: cta1.id,
        fullText,
        combinationHash: hash,
        status: 'APPROVED',
      },
    });
  }

  console.log('\nSeed complete!');
  console.log(`  ${createdVerticals.length} verticals`);
  console.log(`  ${projects.length} projects`);
  console.log(`  ${totalBlocks} blocks (across all verticals)`);
  console.log('  1 sample output');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
