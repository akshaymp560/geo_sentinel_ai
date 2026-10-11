import React, { useEffect, useState } from 'react';
import { Check, ArrowRight, RefreshCw, AlertTriangle } from 'lucide-react';
import { Button, PageFrame, StatusBadge, Notice } from '../common/ui';

const STAGES = [
  'AOI validation',
  'Satellite retrieval (GEE)',
  'Preprocessing and quality screening',
  'ChangeFormer inference',
  'Environmental evidence agents',
  'Evidence fusion',
  'Consistency and quality validation',
  'Qwen interpretation',
  'Persistence and report availability'
];

export default function Screen4Processing({ 
  workflow, 
  analysisStatus, 
  analysisError, 
  startAnalysis, 
  navigateTo 
}) {
  const isComplete = analysisStatus === 'success' || Boolean(workflow?.investigationData?.analytics);
  const isRunning = analysisStatus === 'running';
  const isFailed = analysisStatus === 'error';

  // Animated stage counter while waiting for backend
  const [activeStageIndex, setActiveStageIndex] = useState(0);

  useEffect(() => {
    if (isComplete) {
      setActiveStageIndex(8);
      // Auto-navigate to Explorer after a brief pause
      const timer = setTimeout(() => {
        navigateTo('EXPLORER');
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [isComplete, navigateTo]);

  useEffect(() => {
    if (!isRunning) return;

    // Cycle through stages progressively during the ~30s execution
    const interval = setInterval(() => {
      setActiveStageIndex(prev => (prev < 7 ? prev + 1 : prev));
    }, 3800);

    return () => clearInterval(interval);
  }, [isRunning]);

  const currentStatusBadge = isComplete 
    ? 'COMPLETED' 
    : isRunning 
      ? 'RUNNING' 
      : isFailed 
        ? 'FAILED' 
        : 'IDLE';

  return (
    <PageFrame
      eyebrow="Investigation / Processing"
      title="Autonomous Live Analysis"
      description={
        isComplete 
          ? "Analysis complete. Redirecting to Explorer..." 
          : isRunning 
            ? "Executing Earth Engine acquisition, ChangeFormer ViT, and agent swarm..." 
            : isFailed 
              ? "Analysis encountered an error." 
              : "Ready to initiate analysis."
      }
      actions={<StatusBadge status={currentStatusBadge} />}
    >
      <div className="max-w-3xl border border-zinc-800 bg-zinc-950 p-6 rounded-lg">
        {analysisError && (
          <div className="mb-6">
            <Notice>{analysisError}</Notice>
          </div>
        )}

        <ol className="space-y-0">
          {STAGES.map((stageName, index) => {
            const stageNum = index + 1;
            const stageDone = isComplete || (isRunning && activeStageIndex > index);
            const stageActive = isRunning && activeStageIndex === index;
            const stageStatus = stageDone 
              ? 'COMPLETED' 
              : stageActive 
                ? 'RUNNING' 
                : 'QUEUED';

            return (
              <li key={stageName} className="relative flex gap-4 pb-6 last:pb-0">
                <div
                  className={`z-10 grid h-7 w-7 shrink-0 place-items-center rounded-full border text-xs font-mono transition-colors ${
                    stageDone
                      ? 'border-green-600 text-green-400 bg-green-950/40'
                      : stageActive
                        ? 'border-blue-500 text-blue-300 animate-pulse bg-blue-950/40'
                        : 'border-zinc-800 text-zinc-600 bg-zinc-900'
                  }`}
                >
                  {stageDone ? <Check size={14} /> : stageNum}
                </div>

                {index < STAGES.length - 1 && (
                  <span className="absolute left-3.5 top-7 h-full w-px bg-zinc-800" />
                )}

                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm ${
                      stageActive 
                        ? 'text-white font-medium' 
                        : stageDone 
                          ? 'text-zinc-300' 
                          : 'text-zinc-600'
                    }`}>
                      {stageName}
                    </span>
                    <StatusBadge status={stageStatus} />
                  </div>
                </div>
              </li>
            );
          })}
        </ol>

        {isComplete && (
          <div className="mt-8 flex flex-wrap gap-3 border-t border-zinc-800 pt-5">
            <Button onClick={() => navigateTo('EXPLORER')}>
              Open Explorer <ArrowRight size={15} />
            </Button>
            <Button variant="secondary" onClick={() => navigateTo('EVIDENCE')}>
              Review Evidence
            </Button>
            <Button variant="secondary" onClick={() => navigateTo('REPORT')}>
              View Report
            </Button>
          </div>
        )}

        {isFailed && (
          <div className="mt-8 border-t border-zinc-800 pt-5">
            <Button onClick={startAnalysis}>
              <RefreshCw size={15} /> Retry Analysis
            </Button>
          </div>
        )}
      </div>
    </PageFrame>
  );
}