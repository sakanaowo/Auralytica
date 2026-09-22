import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from './api/client';
import { AppShell } from './components/AppShell';
import { ImportView } from './features/import/ImportView';
import { ExploreView } from './features/explore/ExploreView';
import { DedupView } from './features/dedup/DedupView';
import { DownloadView } from './features/download/DownloadView';

type Step = 'import' | 'explore' | 'deduplicate' | 'download';

export const App: React.FC = () => {
  const getInitialStep = (): Step => {
    const p = window.location.pathname.replace(/^\//, '').split('/')[0];
    if (['import', 'explore', 'deduplicate', 'download'].includes(p)) {
      return p as Step;
    }
    return 'explore';
  };

  const [currentStep, setCurrentStep] = useState<Step>(getInitialStep);

  // Sync with browser back/forward
  useEffect(() => {
    const onPopState = () => {
      setCurrentStep(getInitialStep());
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  // Poll workflow
  const { data: workflow, refetch: refetchWorkflow } = useQuery({
    queryKey: ['workflow'],
    queryFn: () => api.getWorkflow(),
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.batch_locked ? 1500 : 4000;
    },
  });

  const navigate = (step: Step) => {
    setCurrentStep(step);
    if (window.location.pathname !== `/${step}`) {
      window.history.pushState(null, '', `/${step}`);
    }
  };

  const hasImport = !!workflow?.active_import;

  return (
    <AppShell currentStep={currentStep} onNavigate={navigate} workflow={workflow}>
      {/* Empty State when no history has been imported yet */}
      {!hasImport && currentStep !== 'import' ? (
        <div className="max-w-md mx-auto my-auto py-16 text-center space-y-4">
          <div className="glass-panel rounded-2xl p-8 space-y-4 border border-white/10 shadow-xl">
            <h2 className="text-base font-semibold text-zinc-100">Chưa có dữ liệu lịch sử</h2>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Bạn cần nhập folder Google Takeout trước khi có thể duyệt thư viện, đối soát bài trùng hoặc tải audio.
            </p>
            <button
              type="button"
              onClick={() => navigate('import')}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white transition-all shadow-md"
            >
              Mở bước 01 · Import
            </button>
          </div>
        </div>
      ) : (
        <>
          {currentStep === 'import' && (
            <ImportView
              onImportSuccess={() => {
                refetchWorkflow();
                navigate('explore');
              }}
              batchLocked={!!workflow?.batch_locked}
            />
          )}

          {currentStep === 'explore' && (
            <ExploreView
              batchLocked={!!workflow?.batch_locked}
              onRefreshWorkflow={refetchWorkflow}
            />
          )}

          {currentStep === 'deduplicate' && (
            <DedupView onNavigateDownload={() => navigate('download')} />
          )}

          {currentStep === 'download' && (
            <DownloadView
              batchLocked={!!workflow?.batch_locked}
              onRefreshWorkflow={refetchWorkflow}
            />
          )}
        </>
      )}
    </AppShell>
  );
};
