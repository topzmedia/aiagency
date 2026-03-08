import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchBlocks, fetchProjects, fetchVerticals, fetchTemplates, composeOutput } from '../lib/api';
import { Shuffle, Save, Copy, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import LoadingSpinner from '../components/LoadingSpinner';
import type { CopyBlock, CompositionTemplate, Vertical } from '../types';

export default function Composer() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState('');
  const [verticalId, setVerticalId] = useState('');
  const [outputType, setOutputType] = useState('AD_COPY');
  const [templateId, setTemplateId] = useState('default');
  const [selections, setSelections] = useState({
    hookBlockId: '',
    problemBlockId: '',
    discoveryBlockId: '',
    benefitBlockId: '',
    ctaBlockId: '',
  });

  const { data: projects } = useQuery({ queryKey: ['projects'], queryFn: () => fetchProjects() });
  const { data: verticals } = useQuery({ queryKey: ['verticals'], queryFn: fetchVerticals });
  const { data: templates } = useQuery({ queryKey: ['templates'], queryFn: fetchTemplates });

  const blockParams: Record<string, string> = {};
  if (projectId) blockParams.projectId = projectId;
  if (verticalId) blockParams.verticalId = verticalId;

  const { data: blocks } = useQuery({
    queryKey: ['blocks', blockParams],
    queryFn: () => fetchBlocks(blockParams),
    enabled: !!(projectId && verticalId),
  });

  const composeMut = useMutation({
    mutationFn: (data: any) => composeOutput(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outputs'] });
      toast.success('Output saved');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const blocksByType = useMemo(() => {
    if (!blocks) return { hooks: [], problems: [], discoveries: [], benefits: [], ctas: [] };
    return {
      hooks: blocks.filter((b: CopyBlock) => b.type === 'HOOK'),
      problems: blocks.filter((b: CopyBlock) => b.type === 'PROBLEM'),
      discoveries: blocks.filter((b: CopyBlock) => b.type === 'DISCOVERY'),
      benefits: blocks.filter((b: CopyBlock) => b.type === 'BENEFIT'),
      ctas: blocks.filter((b: CopyBlock) => b.type === 'CTA'),
    };
  }, [blocks]);

  const currentTemplate = templates?.find((t: CompositionTemplate) => t.id === templateId);

  // Build preview
  const preview = useMemo(() => {
    if (!currentTemplate || !blocks) return '';
    const blockMap = new Map((blocks as CopyBlock[]).map((b) => [b.id, b]));

    let text = currentTemplate.template;
    const replacements: Record<string, string> = {
      hook: selections.hookBlockId ? blockMap.get(selections.hookBlockId)?.content || '' : '[Select a hook]',
      problem: selections.problemBlockId ? blockMap.get(selections.problemBlockId)?.content || '' : '[Select a problem]',
      discovery: selections.discoveryBlockId ? blockMap.get(selections.discoveryBlockId)?.content || '' : '[Select a discovery]',
      benefit: selections.benefitBlockId ? blockMap.get(selections.benefitBlockId)?.content || '' : '[Select a benefit]',
      cta: selections.ctaBlockId ? blockMap.get(selections.ctaBlockId)?.content || '' : '[Select a CTA]',
    };

    for (const [key, value] of Object.entries(replacements)) {
      text = text.replace(`{${key}}`, value);
    }
    return text;
  }, [currentTemplate, blocks, selections]);

  const wordCount = preview.split(/\s+/).filter((w: string) => w.length > 0).length;
  const charCount = preview.length;
  const speakingTime = Math.ceil((wordCount / 150) * 60);

  function handleProjectChange(id: string) {
    const project = projects?.find((p: any) => p.id === id);
    setProjectId(id);
    if (project) setVerticalId(project.verticalId);
    setSelections({ hookBlockId: '', problemBlockId: '', discoveryBlockId: '', benefitBlockId: '', ctaBlockId: '' });
  }

  function randomize() {
    const pick = (arr: CopyBlock[]) => arr.length ? arr[Math.floor(Math.random() * arr.length)].id : '';
    setSelections({
      hookBlockId: pick(blocksByType.hooks),
      problemBlockId: pick(blocksByType.problems),
      discoveryBlockId: pick(blocksByType.discoveries),
      benefitBlockId: pick(blocksByType.benefits),
      ctaBlockId: pick(blocksByType.ctas),
    });
  }

  function handleSave() {
    if (!projectId || !verticalId) {
      toast.error('Select a project first');
      return;
    }
    composeMut.mutate({
      projectId,
      verticalId,
      outputType,
      templateId,
      ...selections,
    });
  }

  function copyToClipboard() {
    navigator.clipboard.writeText(preview);
    toast.success('Copied to clipboard');
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left Panel - Selectors */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h3 className="font-semibold text-gray-900">Compose Output</h3>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Project</label>
              <select value={projectId} onChange={(e) => handleProjectChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                <option value="">Select...</option>
                {(projects || []).map((p: any) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Output Type</label>
              <select value={outputType} onChange={(e) => setOutputType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                <option value="AD_COPY">Ad Copy</option>
                <option value="VIDEO_SCRIPT">Video Script</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Template</label>
            <select value={templateId} onChange={(e) => setTemplateId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
              {(templates || []).map((t: CompositionTemplate) => (
                <option key={t.id} value={t.id}>{t.name} — {t.description}</option>
              ))}
            </select>
          </div>

          {/* Block Selectors */}
          {currentTemplate?.slots.includes('hook') && (
            <BlockSelector label="Hook" blocks={blocksByType.hooks} value={selections.hookBlockId}
              onChange={(v) => setSelections({ ...selections, hookBlockId: v })} />
          )}
          {currentTemplate?.slots.includes('problem') && (
            <BlockSelector label="Problem" blocks={blocksByType.problems} value={selections.problemBlockId}
              onChange={(v) => setSelections({ ...selections, problemBlockId: v })} />
          )}
          {currentTemplate?.slots.includes('discovery') && (
            <BlockSelector label="Discovery" blocks={blocksByType.discoveries} value={selections.discoveryBlockId}
              onChange={(v) => setSelections({ ...selections, discoveryBlockId: v })} />
          )}
          {currentTemplate?.slots.includes('benefit') && (
            <BlockSelector label="Benefit" blocks={blocksByType.benefits} value={selections.benefitBlockId}
              onChange={(v) => setSelections({ ...selections, benefitBlockId: v })} />
          )}
          {currentTemplate?.slots.includes('cta') && (
            <BlockSelector label="CTA" blocks={blocksByType.ctas} value={selections.ctaBlockId}
              onChange={(v) => setSelections({ ...selections, ctaBlockId: v })} />
          )}

          <button onClick={randomize} disabled={!projectId}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50">
            <Shuffle size={16} /> Randomize
          </button>
        </div>
      </div>

      {/* Right Panel - Preview */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Live Preview</h3>
          <div className="bg-gray-50 rounded-lg p-4 min-h-[200px] whitespace-pre-wrap text-sm text-gray-700">
            {preview || 'Select blocks to see preview...'}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Metadata</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">{charCount}</p>
              <p className="text-xs text-gray-500">Characters</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">{wordCount}</p>
              <p className="text-xs text-gray-500">Words</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-center gap-1">
                <Clock size={16} className="text-gray-400" />
                <p className="text-2xl font-bold text-gray-900">{speakingTime}s</p>
              </div>
              <p className="text-xs text-gray-500">Est. Speaking</p>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={handleSave} disabled={composeMut.isPending || !projectId}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            <Save size={16} /> Save Output
          </button>
          <button onClick={copyToClipboard}
            className="flex items-center gap-2 px-4 py-2.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">
            <Copy size={16} /> Copy
          </button>
        </div>
      </div>
    </div>
  );
}

function BlockSelector({ label, blocks, value, onChange }: {
  label: string; blocks: CopyBlock[]; value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
        <option value="">Select {label.toLowerCase()}...</option>
        {blocks.map((b) => (
          <option key={b.id} value={b.id}>
            {b.label}: {b.content.substring(0, 60)}...
          </option>
        ))}
      </select>
    </div>
  );
}
