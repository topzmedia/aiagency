import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchProjects, fetchVerticals, fetchBlocks, fetchTemplates,
  bulkGenerateOutputs, deleteOutput,
} from '../lib/api';
import { Shuffle, Trash2, Eye, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import type { CopyBlock, CompositionTemplate, GeneratedOutput, Vertical } from '../types';

const PAGE_SIZE = 10;

export default function BulkGenerator() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState('');
  const [verticalId, setVerticalId] = useState('');
  const [outputType, setOutputType] = useState('AD_COPY');
  const [templateId, setTemplateId] = useState('default');
  const [count, setCount] = useState(10);
  const [uniqueOnly, setUniqueOnly] = useState(true);
  const [approvedOnly, setApprovedOnly] = useState(false);
  const [randomize, setRandomize] = useState(true);
  const [locks, setLocks] = useState({
    lockedHookId: '', lockedProblemId: '', lockedDiscoveryId: '',
    lockedBenefitId: '', lockedCtaId: '',
  });
  const [results, setResults] = useState<any>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  const { data: projects } = useQuery({ queryKey: ['projects'], queryFn: () => fetchProjects() });
  const { data: verticals } = useQuery({ queryKey: ['verticals'], queryFn: fetchVerticals });
  const { data: templates } = useQuery({ queryKey: ['templates'], queryFn: fetchTemplates });

  const blockParams: Record<string, string> = { slim: 'true' };
  if (projectId) blockParams.projectId = projectId;
  if (verticalId) blockParams.verticalId = verticalId;

  const { data: blocks } = useQuery({
    queryKey: ['blocks', blockParams],
    queryFn: () => fetchBlocks(blockParams),
    enabled: !!(projectId && verticalId),
  });

  const generateMut = useMutation({
    mutationFn: (data: any) => bulkGenerateOutputs(data),
    onSuccess: (data) => {
      setResults(data);
      setPage(0);
      queryClient.invalidateQueries({ queryKey: ['outputs'] });
      toast.success(`Generated ${data.generated} outputs`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteOutput(id),
    onSuccess: (_, id) => {
      if (results) {
        setResults({
          ...results,
          outputs: results.outputs.filter((o: any) => o.id !== id),
          generated: results.generated - 1,
        });
      }
      queryClient.invalidateQueries({ queryKey: ['outputs'] });
      toast.success('Output deleted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const hookBlocks = (blocks || []).filter((b: CopyBlock) => b.type === 'HOOK');
  const problemBlocks = (blocks || []).filter((b: CopyBlock) => b.type === 'PROBLEM');
  const discoveryBlocks = (blocks || []).filter((b: CopyBlock) => b.type === 'DISCOVERY');
  const benefitBlocks = (blocks || []).filter((b: CopyBlock) => b.type === 'BENEFIT');
  const ctaBlocks = (blocks || []).filter((b: CopyBlock) => b.type === 'CTA');

  function handleProjectChange(id: string) {
    const project = projects?.find((p: any) => p.id === id);
    setProjectId(id);
    if (project) setVerticalId(project.verticalId);
    setLocks({ lockedHookId: '', lockedProblemId: '', lockedDiscoveryId: '', lockedBenefitId: '', lockedCtaId: '' });
  }

  function handleGenerate() {
    if (!projectId || !verticalId) {
      toast.error('Select a project');
      return;
    }
    const data: any = {
      projectId, verticalId, outputType, templateId, count,
      uniqueOnly, approvedOnly, randomize,
    };
    if (locks.lockedHookId) data.lockedHookId = locks.lockedHookId;
    if (locks.lockedProblemId) data.lockedProblemId = locks.lockedProblemId;
    if (locks.lockedDiscoveryId) data.lockedDiscoveryId = locks.lockedDiscoveryId;
    if (locks.lockedBenefitId) data.lockedBenefitId = locks.lockedBenefitId;
    if (locks.lockedCtaId) data.lockedCtaId = locks.lockedCtaId;
    generateMut.mutate(data);
  }

  const paginatedOutputs = results?.outputs?.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE) || [];
  const totalPages = results ? Math.ceil((results.outputs?.length || 0) / PAGE_SIZE) : 0;

  // Build a block id -> label map
  const blockIdMap = new Map((blocks || []).map((b: CopyBlock) => [b.id, b.label]));

  return (
    <div className="space-y-6">
      {/* Settings Panel */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900">Bulk Generation Settings</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Template</label>
            <select value={templateId} onChange={(e) => setTemplateId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
              {(templates || []).map((t: CompositionTemplate) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Number of Outputs</label>
            <input type="number" min={1} max={500} value={count}
              onChange={(e) => setCount(parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={uniqueOnly}
                onChange={(e) => setUniqueOnly(e.target.checked)}
                className="rounded border-gray-300" />
              Unique Only
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={approvedOnly}
                onChange={(e) => setApprovedOnly(e.target.checked)}
                className="rounded border-gray-300" />
              Approved Only
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={randomize}
                onChange={(e) => setRandomize(e.target.checked)}
                className="rounded border-gray-300" />
              Randomize
            </label>
          </div>
        </div>

        {/* Lock Selectors */}
        {projectId && (
          <div className="space-y-3 pt-3 border-t border-gray-100">
            <h4 className="text-sm font-medium text-gray-700">Lock Specific Blocks (Optional)</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <LockSelector label="Lock Hook" blocks={hookBlocks} value={locks.lockedHookId}
                onChange={(v) => setLocks({ ...locks, lockedHookId: v })} />
              <LockSelector label="Lock Problem" blocks={problemBlocks} value={locks.lockedProblemId}
                onChange={(v) => setLocks({ ...locks, lockedProblemId: v })} />
              <LockSelector label="Lock Discovery" blocks={discoveryBlocks} value={locks.lockedDiscoveryId}
                onChange={(v) => setLocks({ ...locks, lockedDiscoveryId: v })} />
              <LockSelector label="Lock Benefit" blocks={benefitBlocks} value={locks.lockedBenefitId}
                onChange={(v) => setLocks({ ...locks, lockedBenefitId: v })} />
              <LockSelector label="Lock CTA" blocks={ctaBlocks} value={locks.lockedCtaId}
                onChange={(v) => setLocks({ ...locks, lockedCtaId: v })} />
            </div>
          </div>
        )}

        <button onClick={handleGenerate} disabled={generateMut.isPending || !projectId}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
          <Shuffle size={16} /> {generateMut.isPending ? 'Generating...' : 'Generate Outputs'}
        </button>
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-gray-900">Results</h3>
              <span className="text-sm text-gray-500">{results.generated} generated / {results.maxPossible} max possible</span>
            </div>
            {results.warning && (
              <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 px-3 py-1.5 rounded-lg">
                <AlertTriangle size={14} /> {results.warning}
              </div>
            )}
          </div>

          {/* Preview Modal */}
          {previewId && (
            <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
              onClick={() => setPreviewId(null)}>
              <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6" onClick={(e) => e.stopPropagation()}>
                <h3 className="font-semibold text-gray-900 mb-3">Output Preview</h3>
                <div className="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-700">
                  {results.outputs.find((o: any) => o.id === previewId)?.fullText}
                </div>
                <button onClick={() => setPreviewId(null)}
                  className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm w-full">
                  Close
                </button>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">#</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Hook</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Problem</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Discovery</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Benefit</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">CTA</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedOutputs.map((output: any, idx: number) => (
                  <tr key={output.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">{page * PAGE_SIZE + idx + 1}</td>
                    <td className="px-4 py-3 text-gray-700 text-xs">{blockIdMap.get(output.hookBlockId) || '—'}</td>
                    <td className="px-4 py-3 text-gray-700 text-xs">{blockIdMap.get(output.problemBlockId) || '—'}</td>
                    <td className="px-4 py-3 text-gray-700 text-xs">{blockIdMap.get(output.discoveryBlockId) || '—'}</td>
                    <td className="px-4 py-3 text-gray-700 text-xs">{blockIdMap.get(output.benefitBlockId) || '—'}</td>
                    <td className="px-4 py-3 text-gray-700 text-xs">{blockIdMap.get(output.ctaBlockId) || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
                        {output.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <button onClick={() => setPreviewId(output.id)}
                          className="p-1 text-gray-400 hover:text-indigo-600"><Eye size={14} /></button>
                        <button onClick={() => deleteMut.mutate(output.id)}
                          className="p-1 text-gray-400 hover:text-red-600"><Trash2 size={14} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4">
              <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
                className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-30">
                <ChevronLeft size={20} />
              </button>
              <span className="text-sm text-gray-500">Page {page + 1} of {totalPages}</span>
              <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
                className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-30">
                <ChevronRight size={20} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function LockSelector({ label, blocks, value, onChange }: {
  label: string; blocks: CopyBlock[]; value: string; onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs">
        <option value="">None (rotate)</option>
        {blocks.map((b) => (
          <option key={b.id} value={b.id}>{b.label}</option>
        ))}
      </select>
    </div>
  );
}
