export interface CompositionTemplate {
  id: string;
  name: string;
  description: string;
  slots: string[];
  template: string;
}

const templates: CompositionTemplate[] = [
  {
    id: 'default',
    name: 'Default (All Blocks)',
    description: 'Hook → Problem → Discovery → Benefit → CTA',
    slots: ['hook', 'problem', 'discovery', 'benefit', 'cta'],
    template: '{hook}\n\n{problem}\n\n{discovery}\n\n{benefit}\n\n{cta}',
  },
  {
    id: 'template_a',
    name: 'Template A (No Discovery)',
    description: 'Hook → Problem → Benefit → CTA',
    slots: ['hook', 'problem', 'benefit', 'cta'],
    template: '{hook}\n\n{problem}\n\n{benefit}\n\n{cta}',
  },
  {
    id: 'template_b',
    name: 'Template B (Discovery First)',
    description: 'Hook → Discovery → Problem → Benefit → CTA',
    slots: ['hook', 'discovery', 'problem', 'benefit', 'cta'],
    template: '{hook}\n\n{discovery}\n\n{problem}\n\n{benefit}\n\n{cta}',
  },
  {
    id: 'template_c',
    name: 'Template C (Short)',
    description: 'Hook → Benefit → CTA',
    slots: ['hook', 'benefit', 'cta'],
    template: '{hook}\n\n{benefit}\n\n{cta}',
  },
];

export function getTemplates(): CompositionTemplate[] {
  return templates;
}

export function getTemplateById(id: string): CompositionTemplate | undefined {
  return templates.find((t) => t.id === id);
}

export function renderTemplate(
  template: CompositionTemplate,
  blocks: Record<string, string>
): string {
  let result = template.template;
  for (const [key, value] of Object.entries(blocks)) {
    result = result.replace(`{${key}}`, value);
  }
  return result;
}
