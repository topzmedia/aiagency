interface BlockExportRow {
  id: string;
  project: string;
  vertical: string;
  type: string;
  label: string;
  content: string;
  tone: string;
  audience: string;
  isApproved: string;
}

interface OutputExportRow {
  id: string;
  project: string;
  vertical: string;
  output_type: string;
  hook_label: string;
  hook_text: string;
  problem_label: string;
  problem_text: string;
  discovery_label: string;
  discovery_text: string;
  benefit_label: string;
  benefit_text: string;
  cta_label: string;
  cta_text: string;
  full_text: string;
  status: string;
}

function escapeCsvField(field: string): string {
  if (field.includes(',') || field.includes('"') || field.includes('\n')) {
    return `"${field.replace(/"/g, '""')}"`;
  }
  return field;
}

function toCsvRow(fields: string[]): string {
  return fields.map(escapeCsvField).join(',');
}

export function blocksToCSV(blocks: BlockExportRow[]): string {
  const headers = [
    'id', 'project', 'vertical', 'type', 'label', 'content',
    'tone', 'audience', 'isApproved',
  ];
  const rows = blocks.map((b) =>
    toCsvRow([
      b.id, b.project, b.vertical, b.type, b.label, b.content,
      b.tone, b.audience, b.isApproved,
    ])
  );
  return [toCsvRow(headers), ...rows].join('\n');
}

export function outputsToCSV(outputs: OutputExportRow[]): string {
  const headers = [
    'id', 'project', 'vertical', 'output_type',
    'hook_label', 'hook_text',
    'problem_label', 'problem_text',
    'discovery_label', 'discovery_text',
    'benefit_label', 'benefit_text',
    'cta_label', 'cta_text',
    'full_text', 'status',
  ];
  const rows = outputs.map((o) =>
    toCsvRow([
      o.id, o.project, o.vertical, o.output_type,
      o.hook_label, o.hook_text,
      o.problem_label, o.problem_text,
      o.discovery_label, o.discovery_text,
      o.benefit_label, o.benefit_text,
      o.cta_label, o.cta_text,
      o.full_text, o.status,
    ])
  );
  return [toCsvRow(headers), ...rows].join('\n');
}
