import { BlockType } from '../types';

interface GenerationParams {
  vertical: string;
  type: BlockType;
  count: number;
  tone?: string;
  audience?: string;
  readingLevel?: string;
  maxLength?: number;
  customInstructions?: string;
  outputType?: string;
}

// Vertical-specific content banks
const contentBank: Record<string, Record<string, string[]>> = {
  'Auto Insurance': {
    HOOK: [
      "Most drivers are overpaying for auto insurance — and they don't even know it.",
      'What if switching your auto insurance could save you hundreds every year?',
      'Your neighbor might be paying half what you pay for the same coverage.',
      'Stop scrolling — this could save you serious money on car insurance.',
      "The auto insurance industry doesn't want you to know this.",
      "Are you still paying full price for auto insurance? Here's why you shouldn't be.",
      'One quick comparison could change what you pay for car insurance forever.',
      "You wouldn't overpay for gas. Why overpay for auto insurance?",
      "Exposed: why your auto insurance bill keeps going up — and how to stop it.",
      "What your insurance agent isn't telling you about your premium.",
      "3 out of 4 drivers could be saving on auto insurance right now.",
      "I switched my auto insurance last month. Here's what happened to my bill.",
    ],
    PROBLEM: [
      "Every month, that auto insurance bill shows up — and every month, it's higher than it should be.",
      "You've been a safe driver for years, but your premium keeps climbing.",
      "Between gas, maintenance, and insurance, driving costs are out of control.",
      "You're paying for coverage you might not even need, and nobody's told you.",
      "Your current insurer isn't rewarding your loyalty — they're counting on your inertia.",
      "One accident years ago and you're still paying the price on your premium.",
      "Rates keep going up, but your coverage hasn't improved at all.",
      "You've been meaning to shop around, but who has the time?",
      "The fine print on your policy? It's designed to confuse you.",
      "Insurance companies spend millions on advertising instead of lowering your rate.",
      "You feel stuck with your current provider because switching seems like a hassle.",
      "Rising premiums are eating into your monthly budget and it's only getting worse.",
    ],
    DISCOVERY: [
      "It turns out, comparing auto insurance quotes takes less than 5 minutes now.",
      "New comparison tools are making it easy to find better rates without the runaround.",
      "Drivers across the country are discovering they can cut their premiums significantly.",
      "There's a smarter way to shop for auto insurance — and it's completely free.",
      "Insurance companies are now competing harder than ever for safe drivers like you.",
      "A new wave of online tools lets you see real quotes side-by-side, no calls needed.",
    ],
    BENEFIT: [
      "You could save hundreds a year — without sacrificing the coverage you need.",
      "Get the same great coverage at a fraction of the cost.",
      "Switch in minutes, save for months — it's that straightforward.",
      "Lock in a lower rate and finally feel good about your insurance bill.",
      "Join thousands of drivers who are keeping more money in their pockets.",
      "Better coverage, better price — that's what smart comparison shopping gets you.",
      "No hidden fees, no surprises — just transparent savings.",
      "Keep your preferred coverage levels and still pay less every month.",
    ],
    CTA: [
      "Compare your free quotes today — it only takes a minute.",
      "Click below to see how much you could save.",
      "Start your free comparison now — no commitment required.",
      "Get your personalized rate in under 60 seconds.",
      "See your savings — tap the button below to get started.",
    ],
  },
  'Home Insurance': {
    HOOK: [
      "Your home is your biggest investment — but is your insurance actually protecting it?",
      "Most homeowners are overpaying for coverage they don't fully understand.",
      "What would happen to your family if disaster struck tomorrow?",
      "Home insurance rates just went up again. But yours doesn't have to.",
      "Think your home is fully covered? You might be surprised.",
      "One storm could cost you everything — unless you have the right policy.",
      "Your home insurance could be costing you thousands more than it should.",
      "Smart homeowners are switching policies and saving big. Here's how.",
      "Is your home insurance keeping up with your home's actual value?",
      "Don't wait for a claim to find out your coverage falls short.",
    ],
    PROBLEM: [
      "Home insurance premiums keep rising, but your coverage stays the same.",
      "You're paying for a policy you set up years ago — and never reviewed.",
      "One claim and your rates skyrocket. It doesn't seem fair.",
      "Your current policy might not cover what you think it covers.",
      "Between the mortgage, taxes, and insurance, homeownership costs are crushing.",
      "You've been loyal to your insurer, but they haven't been loyal to your wallet.",
      "Most homeowners don't realize they're underinsured until it's too late.",
      "The fine print in your policy? It's full of exclusions you never agreed to.",
      "Natural disasters are increasing, but your coverage hasn't kept pace.",
      "Shopping for home insurance feels overwhelming, so most people just don't.",
    ],
    DISCOVERY: [
      "Comparing home insurance quotes is now faster and easier than ever.",
      "New online tools let you see exactly where you're overpaying.",
      "Homeowners are finding better rates by simply comparing options side-by-side.",
      "There are discounts available most homeowners never even ask about.",
    ],
    BENEFIT: [
      "Protect your home and save money — it doesn't have to be one or the other.",
      "Get comprehensive coverage tailored to your home for less.",
      "Sleep better knowing your home and family are properly protected.",
      "Switch in minutes and start saving on your very next bill.",
      "Access bundling discounts and loyalty savings you might be missing.",
      "Full protection, fair price — that's what the right policy looks like.",
    ],
    CTA: [
      "Compare free home insurance quotes now.",
      "See how much you could save — get started in 60 seconds.",
      "Click below to find a better rate for your home.",
    ],
  },
  Roofing: {
    HOOK: [
      "That small leak could turn into a $20,000 problem — fast.",
      "When was the last time you actually looked at your roof?",
      "Your roof is protecting everything you own. Is it up to the job?",
      "Most roof damage is invisible from the ground — until it's too late.",
      "Storm season is coming. Is your roof ready?",
      "A new roof doesn't have to cost a fortune. Here's what smart homeowners do.",
      "Your roof has an expiration date — and it might already be past due.",
      "Ignoring your roof won't make the problem go away. It'll make it worse.",
      "What if you could get a top-quality roof for less than you think?",
      "Stop putting off that roof inspection — it could save you thousands.",
    ],
    PROBLEM: [
      "Missing shingles, water stains, sagging — the signs are there if you look.",
      "Every rain storm is a gamble when your roof is past its prime.",
      "Roof repairs keep adding up, and the problems keep coming back.",
      "You've been putting off a roof replacement because the cost seems too high.",
      "Water damage from a bad roof can destroy insulation, drywall, and even your foundation.",
      "Insurance claims get denied all the time because of deferred roof maintenance.",
      "You got a quote once and it was shockingly high — so you did nothing.",
      "Finding a trustworthy roofer feels impossible with so many fly-by-night companies.",
    ],
    DISCOVERY: [
      "Homeowners are discovering that financing options make a new roof surprisingly affordable.",
      "Free roof inspections are helping homeowners catch problems before they become emergencies.",
      "New roofing materials last longer and cost less to install than ever before.",
      "Many homeowners don't realize their insurance may cover a full roof replacement.",
    ],
    BENEFIT: [
      "A new roof increases your home's value and curb appeal instantly.",
      "Stop worrying about leaks, mold, and water damage for good.",
      "Enjoy lower energy bills with modern, energy-efficient roofing.",
      "Get a roof built to last 30+ years with a full warranty.",
      "Protect your family and your investment with a roof you can trust.",
      "Flexible financing means you can get started now and pay over time.",
    ],
    CTA: [
      "Schedule your free roof inspection today.",
      "Get a no-obligation quote — click below to get started.",
      "See if you qualify for financing — it takes less than a minute.",
    ],
  },
};

// Generic fallback templates for verticals not in the content bank
const genericBank: Record<string, string[]> = {
  HOOK: [
    "Most people are overpaying for {vertical} services — and they don't even realize it.",
    "What if you could get better {vertical} results for less?",
    "Stop settling for overpriced {vertical} solutions.",
    "{vertical} costs are rising. Here's how smart consumers are fighting back.",
    "The {vertical} industry is changing fast. Are you keeping up?",
    "You deserve better when it comes to {vertical}. Here's why.",
    "This one simple change could transform your {vertical} experience.",
    "Don't make another {vertical} decision without seeing this first.",
    "What nobody tells you about {vertical} could be costing you money.",
    "Ready to finally get {vertical} right? Keep reading.",
    "The truth about {vertical} that most companies won't tell you.",
    "{vertical} doesn't have to be this complicated. Or this expensive.",
  ],
  PROBLEM: [
    "You've been dealing with {vertical} headaches for too long.",
    "Every month, {vertical} costs take a bigger bite out of your budget.",
    "The current {vertical} options out there are confusing and overpriced.",
    "You know you need a better {vertical} solution, but where do you even start?",
    "Bad {vertical} decisions are costing families real money.",
    "The {vertical} process is broken — and consumers are paying the price.",
    "You've tried to find better {vertical} options before, but it felt impossible.",
    "Hidden fees and fine print make {vertical} more expensive than it needs to be.",
    "Most {vertical} providers prioritize their profits over your needs.",
    "The old way of handling {vertical} just doesn't work anymore.",
  ],
  DISCOVERY: [
    "A new generation of {vertical} solutions is making things simpler and cheaper.",
    "Smart consumers are finding better {vertical} options with just a few clicks.",
    "The {vertical} market has finally caught up — better options exist now.",
    "New tools are helping people make smarter {vertical} decisions.",
    "People are discovering that {vertical} doesn't have to be painful or expensive.",
    "There's a better way to approach {vertical} — and it's easier than you think.",
  ],
  BENEFIT: [
    "Save time and money with a smarter approach to {vertical}.",
    "Get better {vertical} results without the hassle.",
    "Join thousands who've already found a better {vertical} solution.",
    "Experience the difference that quality {vertical} service makes.",
    "Finally, a {vertical} solution that puts you first.",
    "Better outcomes, lower costs — that's what modern {vertical} looks like.",
    "Take control of your {vertical} decisions with confidence.",
    "Transparent pricing and real results — no more {vertical} surprises.",
  ],
  CTA: [
    "Get started now — see your {vertical} options instantly.",
    "Click below to find the best {vertical} solution for you.",
    "Compare {vertical} options for free — no commitment needed.",
    "Take the first step toward better {vertical} today.",
    "See how much you could save — start your free {vertical} comparison.",
  ],
};

// Tone modifiers
const toneModifiers: Record<string, (text: string) => string> = {
  professional: (text) => text,
  casual: (text) => text.replace(/\. /g, '! ').replace(/\.$/, '!'),
  urgent: (text) => text.toUpperCase().endsWith('!') ? text : text.replace(/[.!?]?$/, '!'),
  friendly: (text) => text,
  authoritative: (text) => text,
};

function getContentPool(vertical: string, type: BlockType): string[] {
  const verticalBank = contentBank[vertical];
  if (verticalBank && verticalBank[type]) {
    return verticalBank[type];
  }
  // Use generic templates with vertical name substituted
  const genericTemplates = genericBank[type] || genericBank.HOOK;
  return genericTemplates.map((t) => t.replace(/\{vertical\}/g, vertical));
}

function shuffleArray<T>(arr: T[]): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

function applyTone(text: string, tone?: string): string {
  if (!tone || !toneModifiers[tone]) return text;
  return toneModifiers[tone](text);
}

function truncateToLength(text: string, maxLength?: number): string {
  if (!maxLength || text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

export interface GeneratedBlock {
  type: BlockType;
  label: string;
  content: string;
  tone?: string;
  audience?: string;
}

export function generateBlocks(params: GenerationParams): GeneratedBlock[] {
  const pool = getContentPool(params.vertical, params.type);
  const shuffled = shuffleArray(pool);
  const results: GeneratedBlock[] = [];

  for (let i = 0; i < params.count; i++) {
    const baseContent = shuffled[i % shuffled.length];
    // Add slight variation if we need more than the pool size
    let content = baseContent;
    if (i >= shuffled.length) {
      const variationPrefixes: Record<string, string[]> = {
        HOOK: ['Listen up — ', 'Think about this: ', 'Here\'s the deal — ', 'Real talk: '],
        PROBLEM: ['The reality is, ', 'Let\'s be honest — ', 'Face it: ', 'Here\'s the thing — '],
        DISCOVERY: ['Good news: ', 'Finally, ', 'Here\'s what changed: ', 'The breakthrough: '],
        BENEFIT: ['The result? ', 'What this means for you: ', 'Bottom line — ', 'The payoff: '],
        CTA: ['Don\'t wait — ', 'Act now: ', 'Your move — ', 'Ready? '],
      };
      const prefixes = variationPrefixes[params.type] || variationPrefixes.HOOK;
      const prefix = prefixes[i % prefixes.length];
      content = prefix + baseContent.charAt(0).toLowerCase() + baseContent.slice(1);
    }

    content = applyTone(content, params.tone);
    content = truncateToLength(content, params.maxLength);

    const typeLabel = params.type.charAt(0) + params.type.slice(1).toLowerCase();
    results.push({
      type: params.type,
      label: `${typeLabel} #${i + 1}`,
      content,
      tone: params.tone,
      audience: params.audience,
    });
  }

  return results;
}
