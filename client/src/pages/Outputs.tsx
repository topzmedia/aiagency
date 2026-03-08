import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchOutputs, fetchProjects, fetchVerticals, updateOutput, deleteOutput,
} from '../lib/api';
import {
  Eye, Copy, Pencil, Trash2, Check, Archive, Search, X, Save,
} from 'lucide-react';
import toast from 'react-hot-toast';
import EmptyState from '../components/EmptyState';
import LoadingSpinner from '../components/LoadingSpinner';
import ConfirmModal from '../components/ConfirmModal';
import type { GeneratedOutput, Vertical } from '../types';

export default function Outputs() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ projectId: '', verticalId: '', outputType: '', status: '', search: '' });
  const [previewOutput, setPreviewOutput] = useState<GeneratedOutput | null>(null);
  const [editingNotes, setEditingNotes] = useState<string | null>(null);
  const [notesText, setNotesText] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<GeneratedOutput | null>(null);

  const params: Record<string, string> = {};
  if (filters.projectId) params.projectId = filters.projectId;
  if (filters.verticalId) params.verticalId = filters.verticalId;
  if (filters.outputType) params.outputType = filters.outputType;
  if (filters.status) params.status = filters.status;
  if (filters.search) params.search = filters.search;

  const { data: outputs, isLoading } = useQuery({
    queryKey: ['outputs', params],
    queryFn: () => fetchOutputs(params),
  });
  const { data: projects } = useQuery({ queryKey: ['projects'], queryFn: () => fetchProjects() });
  const { data: verticals } = useQuery({ queryKey: ['verticals'], queryFn: fetchVerticals });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateOutput(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outputs'] });
      setEditingNotes(null);
      toast.success('Output updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteOutput(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outputs'] });
      setDeleteTarget(null);
      toast.success('Output deleted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  }

  function copyAllVisible() {
    if (!outputs?.length) return;
    const allText = outputs.map((o: GeneratedOutput, i: number) =>
      `--- Output ${i + 1} ---\n${o.fullText}`
    ).join('\n\n');
    navigator.clipboard.writeText(allText);
    toast.success(`Copied ${outputs.length} outputs to clipboard`);
  }

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder="Search outputs..." />
          </div>
          <select value={filters.projectId}
            onChange={(e) => setFilters({ ...filters, projectId: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="">All Projects</option>
            {(projects || []).map((p: any) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select value={filters.verticalId}
            onChange={(e) => setFilters({ ...filters, verticalId: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="">All Verticals</option>
            {(verticals || []).map((v: Vertical) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          <select value={filters.outputType}
            onChange={(e) => setFilters({ ...filters, outputType: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="">All Types</option>
            <option value="AD_COPY">Ad Copy</option>
            <option value="VIDEO_SCRIPT">Video Script</option>
          </select>
          <select value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="">All Status</option>
            <option value="DRAFT">Draft</option>
            <option value="APPROVED">Approved</option>
            <option value="ARCHIVED">Archived</option>
          </select>
          <button onClick={copyAllVisible}
            className="flex items-center gap-1.5 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">
            <Copy size={14} /> Copy All
          </button>
        </div>
      </div>

      {/* Preview Modal */}
      {previewOutput && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={() => setPreviewOutput(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Output Preview</h3>
              <button onClick={() => setPreviewOutput(null)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="space-y-3">
              <div className="flex gap-2 text-xs">
                <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">
                  {previewOutput.outputType.replace('_', ' ')}
                </span>
                <span className={`px-2 py-0.5 rounded-full ${
                  previewOutput.status === 'APPROVED' ? 'bg-green-100 text-green-700' :
                  previewOutput.status === 'ARCHIVED' ? 'bg-gray-100 text-gray-600' :
                  'bg-yellow-100 text-yellow-700'
                }`}>{previewOutput.status}</span>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-700">
                {previewOutput.fullText}
              </div>
              {previewOutput.hookBlock && (
                <div className="text-xs text-gray-500">
                  <strong>Hook:</strong> {previewOutput.hookBlock.label} |
                  <strong> Problem:</strong> {previewOutput.problemBlock?.label || '—'} |
                  <strong> Discovery:</strong> {previewOutput.discoveryBlock?.label || '—'} |
                  <strong> Benefit:</strong> {previewOutput.benefitBlock?.label || '—'} |
                  <strong> CTA:</strong> {previewOutput.ctaBlock?.label || '—'}
                </div>
              )}
              {previewOutput.notes && (
                <div className="text-sm text-gray-500">
                  <strong>Notes:</strong> {previewOutput.notes}
                </div>
              )}
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={() => copyToClipboard(previewOutput.fullText)}
                className="flex items-center gap-1.5 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">
                <Copy size={14} /> Copy
              </button>
              <button onClick={() => setPreviewOutput(null)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Outputs List */}
      {!outputs?.length ? (
        <EmptyState title="No outputs yet" description="Compose or bulk generate outputs first." />
      ) : (
        <div className="space-y-3">
          {outputs.map((output: GeneratedOutput) => (
            <div key={output.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-medium bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">
                      {output.outputType.replace('_', ' ')}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      output.status === 'APPROVED' ? 'bg-green-100 text-green-700' :
                      output.status === 'ARCHIVED' ? 'bg-gray-100 text-gray-600' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>{output.status}</span>
                    <span className="text-xs text-gray-400">
                      {output.project?.name} &middot; {output.vertical?.name}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 line-clamp-3 whitespace-pre-wrap">
                    {output.fullText}
                  </p>
                  {editingNotes === output.id ? (
                    <div className="mt-2 flex gap-2">
                      <input type="text" value={notesText}
                        onChange={(e) => setNotesText(e.target.value)}
                        className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                        placeholder="Add notes..." />
                      <button onClick={() => updateMut.mutate({ id: output.id, data: { notes: notesText } })}
                        className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs"><Save size={14} /></button>
                      <button onClick={() => setEditingNotes(null)}
                        className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs"><X size={14} /></button>
                    </div>
                  ) : output.notes ? (
                    <p className="mt-1 text-xs text-gray-400 italic">Notes: {output.notes}</p>
                  ) : null}
                </div>
                <div className="flex items-center gap-1 ml-4 shrink-0">
                  <button onClick={() => setPreviewOutput(output)}
                    className="p-1.5 text-gray-400 hover:text-indigo-600 rounded" title="Preview">
                    <Eye size={16} />
                  </button>
                  <button onClick={() => copyToClipboard(output.fullText)}
                    className="p-1.5 text-gray-400 hover:text-gray-600 rounded" title="Copy">
                    <Copy size={16} />
                  </button>
                  <button onClick={() => { setEditingNotes(output.id); setNotesText(output.notes || ''); }}
                    className="p-1.5 text-gray-400 hover:text-gray-600 rounded" title="Edit Notes">
                    <Pencil size={16} />
                  </button>
                  {output.status !== 'APPROVED' && (
                    <button onClick={() => updateMut.mutate({ id: output.id, data: { status: 'APPROVED' } })}
                      className="p-1.5 text-gray-400 hover:text-green-600 rounded" title="Approve">
                      <Check size={16} />
                    </button>
                  )}
                  {output.status !== 'ARCHIVED' && (
                    <button onClick={() => updateMut.mutate({ id: output.id, data: { status: 'ARCHIVED' } })}
                      className="p-1.5 text-gray-400 hover:text-gray-600 rounded" title="Archive">
                      <Archive size={16} />
                    </button>
                  )}
                  <button onClick={() => setDeleteTarget(output)}
                    className="p-1.5 text-gray-400 hover:text-red-600 rounded" title="Delete">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        title="Delete Output"
        message="Are you sure you want to delete this output? This cannot be undone."
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
