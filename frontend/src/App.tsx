import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from './api/client';
import { AppShell, AppMode } from './components/AppShell';
import { ImportView } from './features/import/ImportView';
import { ExploreView } from './features/explore/ExploreView';
import { DedupView } from './features/dedup/DedupView';
import { DownloadView } from './features/download/DownloadView';
import { PlayerWorkspace } from './features/player/PlayerWorkspace';
import { AudioPlayerProvider } from './context/AudioPlayerContext';

type Step = 'import' | 'explore' | 'deduplicate' | 'download';

export const App: React.FC = () => {
  const getInitialRoute = (): { mode: AppMode; step: Step } => {
    const p = window.location.pathname.replace(/^\//, '').split('/')[0];
    if (p === 'player') {
      return { mode: 'player', step: 'explore' };
    }
    if (['import', 'explore', 'deduplicate', 'download'].includes(p)) {
      return { mode: 'takeout', step: p as Step };
    }
    return { mode: 'takeout', step: 'explore' };
  };

  const [appMode, setAppMode] = useState<AppMode>(() => getInitialRoute().mode);
  const [currentStep, setCurrentStep] = useState<Step>(() => getInitialRoute().step);

  // Sync with browser back/forward
  useEffect(() => {
    const onPopState = () => {
      const route = getInitialRoute();
      setAppMode(route.mode);
      setCurrentStep(route.step);
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

  const navigateStep = (step: Step) => {
    setCurrentStep(step);
    setAppMode('takeout');
    if (window.location.pathname !== `/${step}`) {
      window.history.pushState(null, '', `/${step}`);
    }
  };

  const handleModeChange = (mode: AppMode) => {
    setAppMode(mode);
    if (mode === 'player') {
      if (window.location.pathname !== '/player') {
        window.history.pushState(null, '', '/player');
      }
    } else {
      if (window.location.pathname !== `/${currentStep}`) {
        window.history.pushState(null, '', `/${currentStep}`);
      }
    }
  };

  const hasImport = !workflow || Boolean(workflow.active_import);

  return (
    <AudioPlayerProvider>
      <AppShell
        appMode={appMode}
        onModeChange={handleModeChange}
        currentStep={currentStep}
        onNavigate={navigateStep}
        workflow={workflow}
      >
        {appMode === 'player' ? (
          <PlayerWorkspace />
        ) : (
          <>
            {/* Empty State when no history has been imported yet */}
            {!hasImport && currentStep !== 'import' ? (
              <div className="max-w-md mx-auto my-auto py-16 text-center space-y-4">
                <div className="glass-panel rounded-2xl p-8 space-y-4 border border-white/10 shadow-xl">
                  <h2 className="text-base font-semibold text-zinc-100">
                    Chưa có dữ liệu lịch sử
                  </h2>
                  <p className="text-xs text-zinc-400 leading-relaxed">
                    Bạn cần nhập folder Google Takeout trước khi có thể duyệt thư viện, đối soát bài trùng hoặc tải audio.
                  </p>
                  <button
                    type="button"
                    onClick={() => navigateStep('import')}
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
                      navigateStep('explore');
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
                  <DedupView onNavigateDownload={() => navigateStep('download')} />
                )}

                {currentStep === 'download' && (
                  <DownloadView
                    batchLocked={!!workflow?.batch_locked}
                    onRefreshWorkflow={refetchWorkflow}
                  />
                )}
              </>
            )}
          </>
        )}
      </AppShell>
    </AudioPlayerProvider>
  );
};
