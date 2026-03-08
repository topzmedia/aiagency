import { useQuery } from '@tanstack/react-query';
import { fetchProjects, fetchBlocks, fetchOutputs, fetchVerticals } from '../lib/api';
import { FolderOpen, Layers, FileOutput, BarChart3 } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';

export default function Dashboard() {
  const { data: projects, isLoading: loadingProjects } = useQuery({ queryKey: ['projects'], queryFn: () => fetchProjects() });
  const { data: blocks, isLoading: loadingBlocks } = useQuery({ queryKey: ['blocks'], queryFn: () => fetchBlocks() });
  const { data: outputs, isLoading: loadingOutputs } = useQuery({ queryKey: ['outputs'], queryFn: () => fetchOutputs() });
  const { data: verticals } = useQuery({ queryKey: ['verticals'], queryFn: fetchVerticals });

  if (loadingProjects || loadingBlocks || loadingOutputs) return <LoadingSpinner />;

  const totalProjects = projects?.length || 0;
  const totalBlocks = blocks?.length || 0;
  const totalOutputs = outputs?.length || 0;

  // Outputs by vertical
  const outputsByVertical: Record<string, number> = {};
  outputs?.forEach((o: any) => {
    const name = o.vertical?.name || 'Unknown';
    outputsByVertical[name] = (outputsByVertical[name] || 0) + 1;
  });

  // Recent outputs (last 5)
  const recentOutputs = (outputs || []).slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard icon={FolderOpen} label="Total Projects" value={totalProjects} color="bg-blue-500" />
        <SummaryCard icon={Layers} label="Total Blocks" value={totalBlocks} color="bg-green-500" />
        <SummaryCard icon={FileOutput} label="Total Outputs" value={totalOutputs} color="bg-purple-500" />
        <SummaryCard icon={BarChart3} label="Verticals" value={verticals?.length || 0} color="bg-orange-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Outputs by Vertical */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase mb-4">Outputs by Vertical</h3>
          {Object.keys(outputsByVertical).length === 0 ? (
            <p className="text-sm text-gray-400">No outputs yet.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(outputsByVertical).map(([name, count]) => (
                <div key={name} className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">{name}</span>
                  <span className="text-sm font-semibold text-gray-900 bg-gray-100 px-2.5 py-0.5 rounded-full">
                    {count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Outputs */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase mb-4">Recent Outputs</h3>
          {recentOutputs.length === 0 ? (
            <p className="text-sm text-gray-400">No outputs yet.</p>
          ) : (
            <div className="space-y-3">
              {recentOutputs.map((output: any) => (
                <div key={output.id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-indigo-600">{output.outputType.replace('_', ' ')}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      output.status === 'APPROVED' ? 'bg-green-100 text-green-700' :
                      output.status === 'ARCHIVED' ? 'bg-gray-100 text-gray-600' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {output.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 line-clamp-2">{output.fullText.substring(0, 100)}...</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-4">
      <div className={`${color} p-3 rounded-lg`}>
        <Icon size={24} className="text-white" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  );
}
