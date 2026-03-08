import { getExportURL } from '../lib/api';
import { Download, FileText, FileJson, Copy } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { fetchBlocks, fetchOutputs } from '../lib/api';
import toast from 'react-hot-toast';

export default function Export() {
  const { data: blocks } = useQuery({ queryKey: ['blocks'], queryFn: () => fetchBlocks() });
  const { data: outputs } = useQuery({ queryKey: ['outputs'], queryFn: () => fetchOutputs() });

  function copyAllOutputs() {
    if (!outputs?.length) {
      toast.error('No outputs to copy');
      return;
    }
    const allText = outputs.map((o: any, i: number) =>
      `--- Output ${i + 1} (${o.status}) ---\n${o.fullText}`
    ).join('\n\n');
    navigator.clipboard.writeText(allText);
    toast.success(`Copied ${outputs.length} outputs to clipboard`);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Export Data</h3>
        <p className="text-sm text-gray-500 mb-6">Download your blocks and outputs in various formats.</p>

        <div className="space-y-4">
          <ExportCard
            icon={FileText}
            title="Blocks CSV"
            description={`Export all ${blocks?.length || 0} blocks as CSV`}
            href={getExportURL('blocks.csv')}
          />
          <ExportCard
            icon={FileText}
            title="Outputs CSV"
            description={`Export all ${outputs?.length || 0} outputs as CSV with full block details`}
            href={getExportURL('outputs.csv')}
          />
          <ExportCard
            icon={FileJson}
            title="Outputs JSON"
            description={`Export all ${outputs?.length || 0} outputs as structured JSON`}
            href={getExportURL('outputs.json')}
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Copy to Clipboard</h3>
        <p className="text-sm text-gray-500 mb-4">Copy all output text to your clipboard.</p>
        <button onClick={copyAllOutputs}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
          <Copy size={16} /> Copy All Outputs ({outputs?.length || 0})
        </button>
      </div>
    </div>
  );
}

function ExportCard({ icon: Icon, title, description, href }: {
  icon: any; title: string; description: string; href: string;
}) {
  return (
    <a
      href={href}
      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
    >
      <div className="flex items-center gap-3">
        <div className="p-2 bg-white rounded-lg border border-gray-200">
          <Icon size={20} className="text-gray-600" />
        </div>
        <div>
          <h4 className="text-sm font-medium text-gray-900">{title}</h4>
          <p className="text-xs text-gray-500">{description}</p>
        </div>
      </div>
      <Download size={18} className="text-gray-400 group-hover:text-indigo-600" />
    </a>
  );
}
