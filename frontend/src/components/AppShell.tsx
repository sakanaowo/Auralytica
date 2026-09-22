import React from 'react';
import { WorkflowState } from '../api/types';

interface AppShellProps {
  currentStep: 'import' | 'explore' | 'deduplicate' | 'download';
  onNavigate: (step: 'import' | 'explore' | 'deduplicate' | 'download') => void;
  workflow?: WorkflowState;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentStep,
  onNavigate,
  workflow,
  children,
}) => {
  const steps: Array<{ key: 'import' | 'explore' | 'deduplicate' | 'download'; label: string; num: string }> = [
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
      <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-[#09090b]/80 backdrop-blur-xl px-6 py-3 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3 shrink-0">
          <a
            href="/"
            onClick={(e) => {
              e.preventDefault();
              onNavigate(workflow?.active_import ? 'explore' : 'import');
            }}
            className="text-base font-bold tracking-tight text-zinc-100 hover:text-white transition-colors select-none"
          >
            auralytica
          </a>
          <span className="text-xs font-mono tracking-wider uppercase px-1.5 py-0.5 rounded border border-white/10 text-zinc-400 bg-white/[0.02]">
            Local
          </span>
        </div>

        {/* 4-Step Text-Driven Stepper */}
        <nav className="flex items-center gap-1.5 p-1 rounded-xl bg-zinc-950/60 border border-white/[0.06]">
          {steps.map((s) => {
            const isActive = currentStep === s.key;
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => onNavigate(s.key)}
                className={`px-3 py-1.5 text-xs rounded-lg transition-all select-none font-medium flex items-center gap-1.5 ${isActive
                    ? 'bg-zinc-800 text-zinc-100 border border-white/10 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                  }`}
              >
                <span className="text-xs font-mono text-zinc-500">{s.num}</span>
                <span>{s.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Status indicator on the right */}
        {/* <div className="flex items-center gap-3 shrink-0 text-xs text-zinc-400">
          {workflow ? (
            <div className="flex items-center gap-2">
              {workflow.batch_locked && (
                <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  Đang tải audio
                </span>
              )}
              {workflow.active_import ? (
                <span className="text-xs font-mono text-zinc-400">
                  {workflow.counts.music.toLocaleString('vi-VN')} Nhạc · {workflow.counts.rest.toLocaleString('vi-VN')} Còn lại
                </span>
              ) : (
                <span className="text-xs text-zinc-500">Chưa nhập lịch sử</span>
              )}
            </div>
          ) : (
            <span className="text-xs text-zinc-500 font-mono">Đang kết nối...</span>
          )}
        </div> */}
      </header>

      {/* Main Content Area */}
      <main
        className={`relative z-10 flex-1 flex flex-col ${currentStep === 'explore' ? 'h-[calc(100vh-61px)] overflow-hidden p-4' : 'p-6'
          }`}
      >
        {children}
      </main>
    </div>
  );
};
