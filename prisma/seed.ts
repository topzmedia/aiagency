import { PrismaClient } from '@prisma/client';
import crypto from 'crypto';

const prisma = new PrismaClient();

function createHash(...parts: string[]): string {
  return crypto.createHash('sha256').update(parts.join(':')).digest('hex').substring(0, 16);
}

async function main() {
  console.log('Seeding database...');

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

  const autoInsurance = createdVerticals.find((v) => v.slug === 'auto-insurance')!;
  const homeInsurance = createdVerticals.find((v) => v.slug === 'home-insurance')!;

  // Create demo projects
  const project1 = await prisma.project.create({
    data: {
      name: 'Auto Insurance Q1 Campaign',
      description: 'First quarter paid social campaign for auto insurance vertical',
      verticalId: autoInsurance.id,
    },
  });

  const project2 = await prisma.project.create({
    data: {
      name: 'Home Insurance Spring Push',
      description: 'Spring season home insurance campaign',
      verticalId: homeInsurance.id,
    },
  });

  // Create demo blocks for Auto Insurance
  const demoBlocks = [
    { type: 'HOOK', label: 'Hook #1', content: "Most drivers are overpaying for auto insurance — and they don't even know it.", tone: 'professional', audience: 'general' },
    { type: 'HOOK', label: 'Hook #2', content: 'What if switching your auto insurance could save you hundreds every year?', tone: 'professional', audience: 'general' },
    { type: 'HOOK', label: 'Hook #3', content: 'Your neighbor might be paying half what you pay for the same coverage.', tone: 'casual', audience: 'general' },
    { type: 'PROBLEM', label: 'Problem #1', content: "Every month, that auto insurance bill shows up — and every month, it's higher than it should be.", tone: 'professional', audience: 'general' },
    { type: 'PROBLEM', label: 'Problem #2', content: "You've been a safe driver for years, but your premium keeps climbing.", tone: 'professional', audience: 'general' },
    { type: 'PROBLEM', label: 'Problem #3', content: 'Between gas, maintenance, and insurance, driving costs are out of control.', tone: 'casual', audience: 'general' },
    { type: 'DISCOVERY', label: 'Discovery #1', content: 'It turns out, comparing auto insurance quotes takes less than 5 minutes now.', tone: 'professional', audience: 'general' },
    { type: 'DISCOVERY', label: 'Discovery #2', content: 'New comparison tools are making it easy to find better rates without the runaround.', tone: 'professional', audience: 'general' },
    { type: 'BENEFIT', label: 'Benefit #1', content: 'You could save hundreds a year — without sacrificing the coverage you need.', tone: 'professional', audience: 'general' },
    { type: 'BENEFIT', label: 'Benefit #2', content: 'Get the same great coverage at a fraction of the cost.', tone: 'professional', audience: 'general' },
    { type: 'BENEFIT', label: 'Benefit #3', content: "Switch in minutes, save for months — it's that straightforward.", tone: 'casual', audience: 'general' },
    { type: 'CTA', label: 'CTA #1', content: 'Compare your free quotes today — it only takes a minute.', tone: 'professional', audience: 'general' },
    { type: 'CTA', label: 'CTA #2', content: 'Click below to see how much you could save.', tone: 'professional', audience: 'general' },
  ];

  const createdBlocks = [];
  for (const block of demoBlocks) {
    const created = await prisma.copyBlock.create({
      data: {
        ...block,
        projectId: project1.id,
        verticalId: autoInsurance.id,
        isApproved: true,
      },
    });
    createdBlocks.push(created);
  }

  // Create demo outputs
  const hook1 = createdBlocks.find((b) => b.label === 'Hook #1')!;
  const problem1 = createdBlocks.find((b) => b.label === 'Problem #1')!;
  const discovery1 = createdBlocks.find((b) => b.label === 'Discovery #1')!;
  const benefit1 = createdBlocks.find((b) => b.label === 'Benefit #1')!;
  const cta1 = createdBlocks.find((b) => b.label === 'CTA #1')!;

  const fullText = `${hook1.content}\n\n${problem1.content}\n\n${discovery1.content}\n\n${benefit1.content}\n\n${cta1.content}`;
  const hash = createHash('default', 'AD_COPY', hook1.id, problem1.id, discovery1.id, benefit1.id, cta1.id);

  await prisma.generatedOutput.create({
    data: {
      projectId: project1.id,
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

  const hook2 = createdBlocks.find((b) => b.label === 'Hook #2')!;
  const problem2 = createdBlocks.find((b) => b.label === 'Problem #2')!;
  const benefit2 = createdBlocks.find((b) => b.label === 'Benefit #2')!;
  const cta2 = createdBlocks.find((b) => b.label === 'CTA #2')!;

  const fullText2 = `${hook2.content}\n\n${problem2.content}\n\n${benefit2.content}\n\n${cta2.content}`;
  const hash2 = createHash('template_a', 'AD_COPY', hook2.id, problem2.id, '', benefit2.id, cta2.id);

  await prisma.generatedOutput.create({
    data: {
      projectId: project1.id,
      verticalId: autoInsurance.id,
      outputType: 'AD_COPY',
      hookBlockId: hook2.id,
      problemBlockId: problem2.id,
      benefitBlockId: benefit2.id,
      ctaBlockId: cta2.id,
      fullText: fullText2,
      combinationHash: hash2,
      status: 'DRAFT',
    },
  });

  console.log('Seed complete!');
  console.log(`  ${createdVerticals.length} verticals`);
  console.log('  2 projects');
  console.log(`  ${createdBlocks.length} blocks`);
  console.log('  2 outputs');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
