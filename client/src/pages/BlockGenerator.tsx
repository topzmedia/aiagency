import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchProjects, fetchVerticals, generateBlocks, updateBlock, deleteBlock } from '../lib/api';
import { Wand2, Pencil, Trash2, Copy, Check, X, Save } from 'lucide-react';
import toast from 'react-hot-toast';
import LoadingSpinner from '../components/LoadingSpinner';
import type { Vertical, CopyBlock } from '../types';

const BLOCK_TYPE_COLORS: Record<string, string> = {
  HOOK: 'bg-blue-100 text-blue-700',
  PROBLEM: 'bg-red-100 text-red-700',
  DISCOVERY: 'bg-yellow-100 text-yellow-700',
  BENEFIT: 'bg-green-100 text-green-700',
  CTA: 'bg-purple-100 text-purple-700',
};

export default function BlockGenerator() {
  const queryClient = useQueryClient();
  const [generatedBlocks, setGeneratedBlocks] = useState<CopyBlock[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const [form, setForm] = useState({
    projectId: '',
    verticalId: '',
    outputType: 'AD_COPY' as string,
    hooks: 5,
    problems: 5,
    discoveries: 3,
    benefits: 4,
    ctas: 3,
    tone: '',
    audience: '',
    readingLevel: '',
    maxLength: 0,
    customInstructions: '',
  });

  const { data: projects } = useQuery({ queryKey: ['projects'], queryFn: () => fetchProjects() });
  const { data: verticals } = useQuery({ queryKey: ['verticals'], queryFn: fetchVerticals });

  const generateMut = useMutation({
    mutationFn: (data: any) => generateBlocks(data),
    onSuccess: (data) => {
      setGeneratedBlocks(data);
      queryClient.invalidateQueries({ queryKey: ['blocks'] });
      toast.success(`Generated ${data.length} blocks`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateBlock(id, data),
    onSuccess: (updated) => {
      setGeneratedBlocks((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
      setEditingId(null);
      toast.success('Block updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteBlock(id),
    onSuccess: (_, id) => {
      setGeneratedBlocks((prev) => prev.filter((b) => b.id !== id));
      queryClient.invalidateQueries({ queryKey: ['blocks'] });
      toast.success('Block deleted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function handleProjectChange(projectId: string) {
    const project = projects?.find((p: any) => p.id === projectId);
    setForm({
      ...form,
      projectId,
      verticalId: project?.verticalId || form.verticalId,
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.projectId || !form.verticalId) {
      toast.error('Project and vertical are required');
      return;
    }
    const total = form.hooks + form.problems + form.discoveries + form.benefits + form.ctas;
    if (total === 0) {
      toast.error('Request at least one block');
      return;
    }
    generateMut.mutate({
      ...form,
      maxLength: form.maxLength > 0 ? form.maxLength : undefined,
      tone: form.tone || undefined,
      audience: form.audience || undefined,
      readingLevel: form.readingLevel || undefined,
      customInstructions: form.customInstructions || undefined,
    });
  }

  function handleDuplicate(block: CopyBlock) {
    setGeneratedBlocks((prev) => [
      ...prev,
      { ...block, id: block.id + '-dup-' + Date.now(), label: block.label + ' (copy)' },
    ]);
    toast.success('Block duplicated locally');
  }

  function toggleApprove(block: CopyBlock) {
    updateMut.mutate({ id: block.id, data: { isApproved: !block.isApproved } });
  }

  // Group blocks by type
  const grouped = generatedBlocks.reduce<Record<string, CopyBlock[]>>((acc, block) => {
    if (!acc[block.type]) acc[block.type] = [];
    acc[block.type].push(block);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Generation Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <h3 className="font-semibold text-gray-900 mb-2">Generate Copy Blocks</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Project</label>
            <select
              value={form.projectId}
              onChange={(e) => handleProjectChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">Select project...</option>
              {(projects || []).map((p: any) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Vertical</label>
            <select
              value={form.verticalId}
              onChange={(e) => setForm({ ...form, verticalId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">Select vertical...</option>
              {(verticals || []).map((v: Vertical) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Output Type</label>
            <select
              value={form.outputType}
              onChange={(e) => setForm({ ...form, outputType: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="AD_COPY">Ad Copy</option>
              <option value="VIDEO_SCRIPT">Video Script</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { key: 'hooks', label: 'Hooks' },
            { key: 'problems', label: 'Problems' },
            { key: 'discoveries', label: 'Discoveries' },
            { key: 'benefits', label: 'Benefits' },
            { key: 'ctas', label: 'CTAs' },
          ].map(({ key, label }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type="number"
                min={0}
                max={50}
                value={(form as any)[key]}
                onChange={(e) => setForm({ ...form, [key]: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tone</label>
            <select
              value={form.tone}
              onChange={(e) => setForm({ ...form, tone: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">Default</option>
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="urgent">Urgent</option>
              <option value="friendly">Friendly</option>
              <option value="authoritative">Authoritative</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Audience</label>
            <input
              type="text"
              value={form.audience}
              onChange={(e) => setForm({ ...form, audience: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder="e.g. homeowners 35-55"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Length (chars)</label>
            <input
              type="number"
              min={0}
              value={form.maxLength}
              onChange={(e) => setForm({ ...form, maxLength: parseInt(e.target.value) || 0 })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder="0 = no limit"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Custom Instructions</label>
          <textarea
            value={form.customInstructions}
            onChange={(e) => setForm({ ...form, customInstructions: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            rows={2}
            placeholder="Any additional instructions for generation..."
          />
        </div>

        <button
          type="submit"
          disabled={generateMut.isPending}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          <Wand2 size={16} />
          {generateMut.isPending ? 'Generating...' : 'Generate Blocks'}
        </button>
      </form>

      {/* Generated Blocks */}
      {Object.entries(grouped).map(([type, blocks]) => (
        <div key={type} className="space-y-3">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full ${BLOCK_TYPE_COLORS[type]}`}>{type}</span>
            <span className="text-sm text-gray-500">({blocks.length})</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {blocks.map((block) => (
              <div key={block.id} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">{block.label}</span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => toggleApprove(block)}
                      className={`p-1 rounded ${block.isApproved ? 'text-green-600' : 'text-gray-400 hover:text-green-600'}`}
                      title={block.isApproved ? 'Approved' : 'Approve'}
                    >
                      <Check size={16} />
                    </button>
                    <button
                      onClick={() => { setEditingId(block.id); setEditContent(block.content); }}
                      className="p-1 text-gray-400 hover:text-gray-600 rounded"
                    >
                      <Pencil size={16} />
                    </button>
                    <button onClick={() => handleDuplicate(block)} className="p-1 text-gray-400 hover:text-gray-600 rounded">
                      <Copy size={16} />
                    </button>
                    <button onClick={() => deleteMut.mutate(block.id)} className="p-1 text-gray-400 hover:text-red-600 rounded">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                {editingId === block.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      rows={3}
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => updateMut.mutate({ id: block.id, data: { content: editContent } })}
                        className="flex items-center gap-1 px-3 py-1 bg-indigo-600 text-white rounded text-xs"
                      >
                        <Save size={14} /> Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                      >
                        <X size={14} /> Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-600">{block.content}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
