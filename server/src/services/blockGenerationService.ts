import { BlockType } from '../types';
import { contentBank } from '../data/contentBank';

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
