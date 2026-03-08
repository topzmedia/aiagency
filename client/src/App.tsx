import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import BlockGenerator from './pages/BlockGenerator';
import BlockLibrary from './pages/BlockLibrary';
import Composer from './pages/Composer';
import BulkGenerator from './pages/BulkGenerator';
import Outputs from './pages/Outputs';
import Export from './pages/Export';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="projects" element={<Projects />} />
            <Route path="generator" element={<BlockGenerator />} />
            <Route path="library" element={<BlockLibrary />} />
            <Route path="composer" element={<Composer />} />
            <Route path="bulk" element={<BulkGenerator />} />
            <Route path="outputs" element={<Outputs />} />
            <Route path="export" element={<Export />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" toastOptions={{ duration: 3000 }} />
    </QueryClientProvider>
  );
}
