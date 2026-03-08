import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchBlocks,
  fetchProjects,
  fetchVerticals,
  updateBlock,
  deleteBlock,
  bulkApproveBlocks,
  bulkDeleteBlocks,
} from '../lib/api';
import {
  Pencil, Trash2, Copy, Check, X, Save, Search, LayoutGrid, Table,
  CheckSquare, Trash, ChevronDown,
} from 'lucide-react';
import toast from 'react-hot-toast';
import EmptyState from '../components/EmptyState';
import LoadingSpinner from '../components/LoadingSpinner';
import ConfirmModal from '../components/ConfirmModal';
import type { CopyBlock, Vertical } from '../types';

const BLOCK_TYPE_COLORS: Record<string, string> = {
  HOOK: 'bg-blue-100 text-blue-700',
  PROBLEM: 'bg-red-100 text-red-700',
  DISCOVERY: 'bg-yellow-100 text-yellow-700',
  BENEFIT: 'bg-green-100 text-green-700',
  CTA: 'bg-purple-100 text-purple-700',
};

export default function BlockLibrary() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<'card' | 'table'>('card');
  const [filters, setFilters] = useState({ projectId: '', verticalId: '', type: '', isApproved: '', search: '' });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false);

  const params: Record<string, string> = {};
  if (filters.projectId) params.projectId = filters.projectId;
  if (filters.verticalId) params.verticalId = filters.verticalId;
  if (filters.type) params.type = filters.type;
  if (filters.isApproved) params.isApproved = filters.isApproved;
  if (filters.search) params.search = filters.search;

  const { data: blocks, isLoading } = useQuery({
    queryKey: ['blocks', params],
    queryFn: () => fetchBlocks(params),
  });
  const { data: projects } = useQuery({ queryKey: ['projects'], queryFn: () => fetchProjects() });
  const { data: verticals } = useQuery({ queryKey: ['verticals'], queryFn: fetchVerticals });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateBlock(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocks'] });
      setEditingId(null);
      toast.success('Block updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteBlock(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocks'] });
      toast.success('Block deleted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const bulkApproveMut = useMutation({
    mutationFn: (ids: string[]) => bulkApproveBlocks(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocks'] });
      setSelected(new Set());
      toast.success('Blocks approved');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const bulkDeleteMut = useMutation({
    mutationFn: (ids: string[]) => bulkDeleteBlocks(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocks'] });
      setSelected(new Set());
      setBulkDeleteConfirm(false);
      toast.success('Blocks deleted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function toggleSelect(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  }

  function toggleSelectAll() {
    if (!blocks) return;
    if (selected.size === blocks.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(blocks.map((b: any) => b.id)));
    }
  }

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder="Search blocks..."
            />
          </div>
          <select
            value={filters.projectId}
            onChange={(e) => setFilters({ ...filters, projectId: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">All Projects</option>
            {(projects || []).map((p: any) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            value={filters.verticalId}
            onChange={(e) => setFilters({ ...filters, verticalId: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">All Verticals</option>
            {(verticals || []).map((v: Vertical) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          <select
            value={filters.type}
            onChange={(e) => setFilters({ ...filters, type: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">All Types</option>
            <option value="HOOK">Hook</option>
            <option value="PROBLEM">Problem</option>
            <option value="DISCOVERY">Discovery</option>
            <option value="BENEFIT">Benefit</option>
            <option value="CTA">CTA</option>
          </select>
          <select
            value={filters.isApproved}
            onChange={(e) => setFilters({ ...filters, isApproved: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">All Status</option>
            <option value="true">Approved Only</option>
          </select>
          <div className="flex border border-gray-300 rounded-lg overflow-hidden">
            <button
              onClick={() => setView('card')}
              className={`p-2 ${view === 'card' ? 'bg-indigo-50 text-indigo-600' : 'text-gray-400'}`}
            >
              <LayoutGrid size={16} />
            </button>
            <button
              onClick={() => setView('table')}
              className={`p-2 ${view === 'table' ? 'bg-indigo-50 text-indigo-600' : 'text-gray-400'}`}
            >
              <Table size={16} />
            </button>
          </div>
        </div>

        {selected.size > 0 && (
          <div className="mt-3 flex items-center gap-3 pt-3 border-t border-gray-100">
            <span className="text-sm text-gray-500">{selected.size} selected</span>
            <button
              onClick={() => bulkApproveMut.mutate(Array.from(selected))}
              className="flex items-center gap-1 px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-xs font-medium hover:bg-green-200"
            >
              <CheckSquare size={14} /> Approve
            </button>
            <button
              onClick={() => setBulkDeleteConfirm(true)}
              className="flex items-center gap-1 px-3 py-1.5 bg-red-100 text-red-700 rounded-lg text-xs font-medium hover:bg-red-200"
            >
              <Trash size={14} /> Delete
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      {!blocks?.length ? (
        <EmptyState title="No blocks found" description="Generate blocks or adjust your filters." />
      ) : view === 'card' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {blocks.map((block: CopyBlock) => (
            <div key={block.id} className={`bg-white rounded-lg border p-4 ${selected.has(block.id) ? 'border-indigo-400 ring-1 ring-indigo-200' : 'border-gray-200'}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selected.has(block.id)}
                    onChange={() => toggleSelect(block.id)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm font-medium text-gray-700">{block.label}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${BLOCK_TYPE_COLORS[block.type]}`}>{block.type}</span>
                  {block.isApproved && <Check size={14} className="text-green-600" />}
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => { setEditingId(block.id); setEditContent(block.content); }} className="p-1 text-gray-400 hover:text-gray-600">
                    <Pencil size={14} />
                  </button>
                  <button onClick={() => deleteMut.mutate(block.id)} className="p-1 text-gray-400 hover:text-red-600">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              {editingId === block.id ? (
                <div className="space-y-2">
                  <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={3} />
                  <div className="flex gap-2">
                    <button onClick={() => updateMut.mutate({ id: block.id, data: { content: editContent } })}
                      className="flex items-center gap-1 px-3 py-1 bg-indigo-600 text-white rounded text-xs">
                      <Save size={14} /> Save
                    </button>
                    <button onClick={() => setEditingId(null)}
                      className="flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                      <X size={14} /> Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-600">{block.content}</p>
              )}
              <div className="mt-2 text-xs text-gray-400">
                {(block as any).project?.name} &middot; {(block as any).vertical?.name}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left">
                  <input type="checkbox" checked={selected.size === blocks.length && blocks.length > 0}
                    onChange={toggleSelectAll} className="rounded border-gray-300" />
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Label</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Content</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Project</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {blocks.map((block: CopyBlock) => (
                <tr key={block.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <input type="checkbox" checked={selected.has(block.id)}
                      onChange={() => toggleSelect(block.id)} className="rounded border-gray-300" />
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">{block.label}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${BLOCK_TYPE_COLORS[block.type]}`}>{block.type}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{block.content}</td>
                  <td className="px-4 py-3 text-gray-500">{(block as any).project?.name}</td>
                  <td className="px-4 py-3">
                    {block.isApproved
                      ? <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Approved</span>
                      : <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">Pending</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <button onClick={() => { setEditingId(block.id); setEditContent(block.content); }}
                        className="p-1 text-gray-400 hover:text-gray-600"><Pencil size={14} /></button>
                      <button onClick={() => deleteMut.mutate(block.id)}
                        className="p-1 text-gray-400 hover:text-red-600"><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmModal
        open={bulkDeleteConfirm}
        title="Delete Selected Blocks"
        message={`Are you sure you want to delete ${selected.size} selected blocks? This cannot be undone.`}
        onConfirm={() => bulkDeleteMut.mutate(Array.from(selected))}
        onCancel={() => setBulkDeleteConfirm(false)}
      />
    </div>
  );
}
