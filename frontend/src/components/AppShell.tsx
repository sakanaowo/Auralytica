import React from 'react';
import { WorkflowState } from '../api/types';
import { PersistentPlayerBar } from '../features/player/PersistentPlayerBar';
import { QueueDrawer } from '../features/player/QueueDrawer';
import { FolderDown, Headphones } from 'lucide-react';

export type AppMode = 'takeout' | 'player';

interface AppShellProps {
  appMode: AppMode;
  onModeChange: (mode: AppMode) => void;
  currentStep: 'import' | 'explore' | 'deduplicate' | 'download';
  onNavigate: (step: 'import' | 'explore' | 'deduplicate' | 'download') => void;
  workflow?: WorkflowState;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  appMode,
  onModeChange,
  currentStep,
  onNavigate,
  workflow,
  children,
}) => {
  const steps: Array<{
    key: 'import' | 'explore' | 'deduplicate' | 'download';
    label: string;
    num: string;
  }> = [
    { key: 'import', label: 'Import', num: '01' },
    { key: 'explore', label: 'Explore', num: '02' },
    { key: 'deduplicate', label: 'Deduplicate', num: '03' },
    { key: 'download', label: 'Download', num: '04' },
  ];

  return (
    <div className="relative min-h-screen bg-[#09090b] text-zinc-100 flex flex-col font-sans selection:bg-zinc-800">
      {/* Subtle ambient lighting for frosted glass reflection */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[20%] w-[600px] h-[600px] rounded-full bg-zinc-800/15 blur-[140px]" />
        <div className="absolute bottom-[-10%] right-[15%] w-[700px] h-[700px] rounded-full bg-zinc-700/10 blur-[160px]" />
      </div>

      {/* Top Header Bar */}
      <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-[#09090b]/80 backdrop-blur-xl px-4 md:px-6 py-2.5 flex items-center justify-between gap-4 select-none">
        {/* Left: Brand + Mode Switcher */}
        <div className="flex items-center gap-4 shrink-0">
          <div className="flex items-center gap-2">
            <a
              href="/"
              onClick={(e) => {
                e.preventDefault();
                if (appMode === 'takeout') {
                  onNavigate(workflow?.active_import ? 'explore' : 'import');
                }
              }}
              className="text-base font-bold tracking-tight text-zinc-100 hover:text-white transition-colors select-none"
            >
              auralytica
            </a>
            <span className="text-[10px] font-mono tracking-wider uppercase px-1.5 py-0.5 rounded border border-white/10 text-zinc-400 bg-white/[0.02]">
              Local
            </span>
          </div>

          {/* Top-level Mode Switcher */}
          <div className="flex items-center p-1 rounded-xl bg-zinc-950/80 border border-white/10 shadow-inner">
            <button
              type="button"
              onClick={() => onModeChange('takeout')}
              className={`px-3 py-1 text-xs rounded-lg transition-all font-medium flex items-center gap-1.5 ${
                appMode === 'takeout'
                  ? 'bg-zinc-800 text-zinc-100 border border-white/10 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <FolderDown className="w-3.5 h-3.5" />
              <span>Takeout Studio</span>
            </button>

            <button
              type="button"
              onClick={() => onModeChange('player')}
              className={`px-3 py-1 text-xs rounded-lg transition-all font-medium flex items-center gap-1.5 ${
                appMode === 'player'
                  ? 'bg-zinc-800 text-emerald-400 border border-white/10 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Headphones className="w-3.5 h-3.5" />
              <span>Music Player</span>
            </button>
          </div>
        </div>

        {/* Center: Stepper (Only in Takeout Studio) */}
        {appMode === 'takeout' && (
          <nav className="flex items-center gap-1.5 p-1 rounded-xl bg-zinc-950/60 border border-white/[0.06]">
            {steps.map((s) => {
              const isActive = currentStep === s.key;
              return (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => onNavigate(s.key)}
                  className={`px-3 py-1 text-xs rounded-lg transition-all select-none font-medium flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-zinc-800 text-zinc-100 border border-white/10 shadow-sm'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  <span className="text-[10px] font-mono text-zinc-500">{s.num}</span>
                  <span>{s.label}</span>
                </button>
              );
            })}
          </nav>
        )}

        {/* Right Status */}
        <div className="shrink-0 text-xs text-zinc-400 hidden sm:block">
          {appMode === 'player' ? (
            <span className="text-xs text-zinc-400 font-medium">Trình phát nhạc cục bộ</span>
          ) : workflow?.batch_locked ? (
            <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20">
              Đang tải audio...
            </span>
          ) : workflow?.active_import ? (
            <span className="text-xs font-mono text-zinc-400">
              {workflow.counts.music.toLocaleString('vi-VN')} Nhạc ·{' '}
              {workflow.counts.rest.toLocaleString('vi-VN')} Còn lại
            </span>
          ) : (
            <span className="text-xs text-zinc-500">Chưa nhập lịch sử</span>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main
        className={`relative z-10 flex-1 flex flex-col ${
          appMode === 'player'
            ? 'h-[calc(100vh-53px-80px)] overflow-hidden'
            : currentStep === 'explore'
            ? 'h-[calc(100vh-53px-80px)] overflow-hidden p-4'
            : 'p-6 pb-28'
        }`}
      >
        {children}
      </main>

      {/* Persistent Bottom Audio Player Bar */}
      <PersistentPlayerBar />

      {/* Right Slide-over Queue Drawer */}
      <QueueDrawer />
    </div>
  );
};
