import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import BomManager from './pages/BomManager';
import RiskAnalysis from './pages/RiskAnalysis';
import WhatIf from './pages/WhatIf';
import CrossExposure from './pages/CrossExposure';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/boms" element={<BomManager />} />
              <Route path="/risk" element={<RiskAnalysis />} />
              <Route path="/whatif" element={<WhatIf />} />
              <Route path="/exposure" element={<CrossExposure />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
