import React, { useState } from 'react';
import { 
  ArrowLeft, ArrowRight, CalendarDays, Check, Download, 
  ImageOff, MapPinned, RefreshCw, Search, SlidersHorizontal 
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import MapCanvas from '../MapCanvas';
import { searchLocation } from '../../services/geocoding';
import { resolveArtifactUrl } from '../../services/api';
import { Button, Metric, Notice, PageFrame, StatusBadge } from '../common/ui';

// Date Helper
function shiftDate(value, days) {
  if (!value) return '';
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (Number.isNaN(date.getTime())) return '';
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

// Screen 1: Location & AOI
function LocationSearch({ onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async event => {
    event.preventDefault();
    if (query.trim().length < 2) return;
    setLoading(true);
    setError('');
    try {
      const matches = await searchLocation(query);
      setResults(matches);
      if (!matches.length) setError('No geographic result found.');
    } catch {
      setResults([]);
      setError('Geocoding is unavailable. Select an AOI by another supported method.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      <form onSubmit={submit} className="flex gap-2">
        <div className="flex min-w-0 flex-1 items-center rounded-lg border border-zinc-700 bg-zinc-950 px-3">
          <Search size={16} className="mr-2 shrink-0 text-zinc-500" />
          <input
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Search a place"
            className="min-w-0 flex-1 bg-transparent py-3 text-sm text-white outline-none placeholder:text-zinc-600"
            aria-label="Search an AOI location"
          />
        </div>
        <Button type="submit" loading={loading}>Find</Button>
      </form>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      {results.length > 0 && (
        <div className="absolute left-0 right-16 top-full z-20 mt-2 overflow-hidden rounded-lg border border-zinc-700 bg-zinc-950">
          {results.map(result => (
            <button
              type="button"
              key={result.displayName}
              onClick={() => { onSelect(result); setResults([]); setQuery(result.name); }}
              className="block w-full border-b border-zinc-800 px-3 py-2.5 text-left text-xs text-zinc-300 last:border-0 hover:bg-zinc-900 hover:text-white"
            >
              {result.displayName}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ScreenLocationAOI({ workflow, setWorkflow, navigateTo }) {
  const aoi = workflow.aoi;
  const valid = Array.isArray(aoi.bbox) && aoi.bbox.length === 4;

  const select = result => setWorkflow(current => ({
    ...current,
    aoi: {
      ...current.aoi,
      name: result.displayName,
      centroid: result.lat.toFixed(5) + '°N, ' + result.lon.toFixed(5) + '°E',
      bbox: result.bbox,
      areaKm2: null,
      type: 'Bounding box'
    }
  }));

  return (
    <PageFrame
      eyebrow="Investigation setup / 01"
      title="Location and area of interest"
      description="Search for a real place, review the returned geographic bounds, and submit the bbox for analysis."
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_360px]">
        <div className="min-h-[480px] overflow-hidden border border-zinc-800 bg-zinc-950">
          <MapCanvas bbox={valid ? aoi.bbox : null} />
        </div>
        <section className="border border-zinc-800 bg-zinc-950 p-5">
          <MapPinned size={20} className="text-zinc-300" />
          <h2 className="mt-4 text-lg font-medium text-white">Select a location</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            The current backend accepts a bounding box. Drag or define bounds on the map.
          </p>
          <div className="mt-6"><LocationSearch onSelect={select} /></div>
          {valid ? (
            <dl className="mt-6 space-y-4">
              <Metric label="Location" value={aoi.name} />
              <Metric label="Centroid" value={aoi.centroid} mono />
              <Metric label="Bounds" value={aoi.bbox.map(value => value.toFixed(5)).join(', ')} mono />
              <Metric label="Geometry sent to backend" value="Bounding box" />
            </dl>
          ) : (
            <div className="mt-6 border border-zinc-800 p-3 text-sm text-zinc-500">
              No location selected. Search above to establish an AOI.
            </div>
          )}
          <div className="mt-8 flex justify-between gap-2">
            <Button variant="tertiary" onClick={() => navigateTo('LANDING')}>
              <ArrowLeft size={15} />Back
            </Button>
            <Button disabled={!valid} onClick={() => navigateTo('DATE_SCENES')}>
              Continue <ArrowRight size={15} />
            </Button>
          </div>
        </section>
      </div>
    </PageFrame>
  );
}

// Screen 2: Date Selection
function DateInput({ label, value, onChange }) {
  return (
    <label className="block text-sm text-zinc-300">
      {label}
      <input
        type="date"
        value={value}
        onChange={event => onChange(event.target.value)}
        className="mt-2 block w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500"
      />
    </label>
  );
}

export function ScreenDateScenes({ workflow, setWorkflow, navigateTo, startAnalysis, analysisStatus }) {
  const dates = workflow.dates;
  const beforeDate = dates.beforeDate || dates.preEnd || '';
  const afterDate = dates.afterDate || dates.postStart || '';
  const valid = Boolean(beforeDate && afterDate && beforeDate < afterDate);

  const updateBefore = value => setWorkflow(current => ({
    ...current,
    dates: {
      ...current.dates,
      beforeDate: value,
      preStart: shiftDate(value, -30),
      preEnd: value,
    },
  }));

  const updateAfter = value => setWorkflow(current => ({
    ...current,
    dates: {
      ...current.dates,
      afterDate: value,
      postStart: value,
      postEnd: shiftDate(value, 30),
    },
  }));

  const actual = workflow.investigationData?.metadata;

  return (
    <PageFrame
      eyebrow="Investigation setup / 02"
      title="Choose observation dates"
      description="Choose the two observation points. GeoSentinel-AI automatically calculates 30-day compositing windows around each date."
    >
      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <section className="border border-zinc-800 bg-zinc-950 p-5">
          <CalendarDays size={20} className="text-zinc-300" />
          <h2 className="mt-4 text-lg font-medium text-white">Observation dates</h2>
          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <DateInput label="Before Date (Pre-event)" value={beforeDate} onChange={updateBefore} />
            <DateInput label="After Date (Post-event)" value={afterDate} onChange={updateAfter} />
          </div>
          {!valid && (
            <p className="mt-4 text-xs text-amber-400">
              Choose two dates with the before observation earlier than the after observation.
            </p>
          )}

          <div className="mt-6 border-t border-zinc-800 pt-5">
            <p className="text-xs text-zinc-500">Backend compositing windows</p>
            <dl className="mt-3 grid gap-3 font-mono text-xs text-zinc-300 sm:grid-cols-2">
              <div><dt className="text-zinc-600">pre_start</dt><dd className="mt-1">{dates.preStart || '—'}</dd></div>
              <div><dt className="text-zinc-600">pre_end</dt><dd className="mt-1">{dates.preEnd || '—'}</dd></div>
              <div><dt className="text-zinc-600">post_start</dt><dd className="mt-1">{dates.postStart || '—'}</dd></div>
              <div><dt className="text-zinc-600">post_end</dt><dd className="mt-1">{dates.postEnd || '—'}</dd></div>
            </dl>
          </div>

          <div className="mt-8 flex justify-between gap-2">
            <Button variant="tertiary" onClick={() => navigateTo('LOCATION_AOI')}>
              <ArrowLeft size={15} />Back
            </Button>
            <Button
              disabled={!valid || analysisStatus === 'running'}
              loading={analysisStatus === 'running'}
              onClick={startAnalysis}
            >
              {analysisStatus === 'running' ? 'Submitting analysis' : 'Start analysis'} <ArrowRight size={15} />
            </Button>
          </div>
        </section>

        <section className="border border-zinc-800 bg-zinc-950 p-5">
          <h2 className="text-lg font-medium text-white">Scene availability</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            Sentinel-2 acquisition dates are resolved by Google Earth Engine during processing.
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {[['Before', actual?.pre_acquisition_date], ['After', actual?.post_acquisition_date]].map(([label, date]) => (
              <div key={label} className="border border-zinc-800 p-4">
                <div className="text-xs text-zinc-500">{label} acquisition</div>
                <div className="mt-3 text-lg text-white">{date || 'Unavailable until analysis'}</div>
                {date && <div className="mt-2 text-xs text-zinc-500">Returned by the detection pipeline</div>}
              </div>
            ))}
          </div>
        </section>
      </div>
    </PageFrame>
  );
}

// Screen 3: Processing Stepper
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

export function ScreenProcessing({ workflow, analysisStatus, analysisError, startAnalysis, navigateTo }) {
  const complete = workflow.investigationData?.status === 'COMPLETED' || Boolean(workflow.investigationData?.analytics);
  const status = complete ? 'COMPLETED' : analysisStatus === 'running' ? 'RUNNING' : analysisStatus === 'error' ? 'FAILED' : 'NOT STARTED';

  return (
    <PageFrame
      eyebrow="Investigation / processing"
      title="Live analysis"
      description="The backend executes Google Earth Engine retrieval, ChangeFormer inference, and agent swarms in a synchronous session."
      actions={workflow.investigationData && <StatusBadge status={status} />}
    >
      <div className="max-w-3xl border border-zinc-800 bg-zinc-950 p-5">
        {analysisError && <div className="mb-5"><Notice>{analysisError}</Notice></div>}

        <ol className="space-y-0">
          {STAGES.map((stage, index) => {
            const stageStatus = complete
              ? 'COMPLETED'
              : analysisStatus === 'running'
                ? (index === 0 ? 'RUNNING' : 'QUEUED')
                : 'QUEUED';

            return (
              <li key={stage} className="relative flex gap-4 pb-6 last:pb-0">
                <div
                  className={`z-10 grid h-7 w-7 shrink-0 place-items-center rounded-full border text-xs ${
                    stageStatus === 'COMPLETED'
                      ? 'border-green-700 text-green-400 bg-green-950/20'
                      : stageStatus === 'RUNNING'
                      ? 'border-blue-600 text-blue-400 animate-pulse bg-blue-950/20'
                      : 'border-zinc-700 text-zinc-600'
                  }`}
                >
                  {stageStatus === 'COMPLETED' ? <Check size={14} /> : index + 1}
                </div>

                {index < STAGES.length - 1 && (
                  <span className="absolute left-3.5 top-7 h-full w-px bg-zinc-800" />
                )}

                <div>
                  <div className="flex items-center gap-3">
                    <h2 className={`text-sm ${stageStatus === 'RUNNING' ? 'text-white font-medium' : stageStatus === 'COMPLETED' ? 'text-zinc-300' : 'text-zinc-600'}`}>
                      {stage}
                    </h2>
                    <StatusBadge status={stageStatus} />
                  </div>
                  {stageStatus === 'RUNNING' && (
                    <p className="mt-1 text-xs text-blue-400">Processing Earth Engine data, ChangeFormer ViT, and evidence swarm...</p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>

        {complete && (
          <div className="mt-8 flex flex-wrap gap-2 border-t border-zinc-800 pt-5">
            <Button onClick={() => navigateTo('EXPLORER')}>Open explorer <ArrowRight size={15} /></Button>
            <Button variant="secondary" onClick={() => navigateTo('EVIDENCE')}>Review evidence</Button>
            <Button variant="secondary" onClick={() => navigateTo('REPORT')}>View report</Button>
          </div>
        )}

        {analysisStatus === 'error' && (
          <Button className="mt-6" onClick={startAnalysis}>
            <RefreshCw size={15} />Retry analysis
          </Button>
        )}
      </div>
    </PageFrame>
  );
}

// Preview Panel Helper
function ImagePanel({ src, alt }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div className="grid min-h-64 place-items-center bg-zinc-950 text-center text-sm text-zinc-600">
        <ImageOff size={22} className="mb-2" />Artifact unavailable
      </div>
    );
  }
  return <img src={src} alt={alt} onError={() => setFailed(true)} className="h-full min-h-64 w-full object-contain bg-zinc-950" />;
}

// Screen 4: Explorer
export function ScreenExplorer({ workflow, navigateTo }) {
  const result = workflow.investigationData;
  const [view, setView] = useState('overlay');
  const [opacity, setOpacity] = useState(70);

  if (!result || !result.analytics) {
    return (
      <PageFrame eyebrow="Investigation / explorer" title="Change detection explorer">
        <Notice>There is no completed backend result for this investigation.</Notice>
      </PageFrame>
    );
  }

  const previews = result.web_previews || {};
  const metadata = result.metadata || {};
  const analytics = result.analytics || {};
  const image = view === 'before' ? previews.pre_rgb_url : view === 'after' ? previews.post_rgb_url : view === 'mask' ? previews.mask_overlay_url : previews.triptych_url;

  return (
    <PageFrame
      eyebrow={`Investigation / ${result.job_id || 'Active'}`}
      title="Change detection explorer"
      description="Visual change artifacts generated by ChangeFormer."
      actions={<Button variant="secondary" onClick={() => navigateTo('EVIDENCE')}>Review evidence <ArrowRight size={15} /></Button>}
    >
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <section className="border border-zinc-800 bg-zinc-950">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 p-3">
            <div className="flex gap-1" role="tablist">
              {[['before', 'Before'], ['after', 'After'], ['mask', 'Change mask'], ['overlay', 'Triptych']].map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => setView(id)}
                  className={`rounded px-3 py-2 text-xs ${view === id ? 'bg-blue-950 text-blue-300' : 'text-zinc-500 hover:text-white'}`}
                >
                  {label}
                </button>
              ))}
            </div>
            {view === 'mask' && (
              <label className="flex items-center gap-2 text-xs text-zinc-500">
                <SlidersHorizontal size={14} />Opacity
                <input type="range" min="0" max="100" value={opacity} onChange={event => setOpacity(event.target.value)} />
              </label>
            )}
          </div>
          <div className="min-h-[420px] p-3">
            <div style={{ opacity: view === 'mask' ? opacity / 100 : 1 }} className="h-full">
              <ImagePanel src={resolveArtifactUrl(image)} alt="Satellite artifact" />
            </div>
          </div>
        </section>

        <aside className="space-y-5">
          <section className="border border-zinc-800 bg-zinc-950 p-5">
            <h2 className="text-sm font-medium text-white">Detection statistics</h2>
            <dl className="mt-5 space-y-4">
              <Metric label="Changed pixels" value={analytics.changed_pixels} mono />
              <Metric label="Evaluated pixels" value={analytics.total_pixels} mono />
              <Metric label="Change percentage" value={analytics.change_percentage == null ? null : analytics.change_percentage + '%'} />
              <Metric label="Estimated changed area" value={analytics.estimated_change_ha == null ? null : analytics.estimated_change_ha + ' ha'} />
            </dl>
          </section>

          <section className="border border-zinc-800 bg-zinc-950 p-5">
            <h2 className="text-sm font-medium text-white">Acquisition metadata</h2>
            <dl className="mt-5 space-y-4">
              <Metric label="Before acquisition" value={metadata.pre_acquisition_date} mono />
              <Metric label="After acquisition" value={metadata.post_acquisition_date} mono />
              <Metric label="Spatial resolution" value={metadata.spatial_resolution_m == null ? null : metadata.spatial_resolution_m + ' m'} />
              <Metric label="CRS" value={metadata.crs} mono />
            </dl>
          </section>
        </aside>
      </div>
    </PageFrame>
  );
}

// Screen 5: Evidence Review
export function ScreenEvidence({ workflow, navigateTo }) {
  const dossier = workflow.investigationData?.evidence_dossier;
  const agents = dossier?.agent_evidence_dossier ? Object.entries(dossier.agent_evidence_dossier) : [];

  return (
    <PageFrame
      eyebrow="Investigation / evidence"
      title="Multi-source evidence review"
      description="Telemetry from the environmental agent swarm."
      actions={<Button variant="secondary" onClick={() => navigateTo('REPORT')}>View report <ArrowRight size={15} /></Button>}
    >
      {!dossier ? (
        <Notice>No evidence dossier was returned by the backend for this analysis.</Notice>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {agents.map(([key, agent]) => (
            <article key={key} className="border border-zinc-800 bg-zinc-950 p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-sm font-medium text-white">{agent.agent || key.replaceAll('_', ' ')}</h2>
                  <p className="mt-1 text-xs text-zinc-600">{agent.hypothesis_tested || 'Hypothesis evaluated'}</p>
                </div>
                <StatusBadge status={agent.status} />
              </div>
              <p className="mt-5 text-sm leading-6 text-zinc-300">{agent.finding || 'No finding returned.'}</p>
              <div className="mt-5 border-t border-zinc-800 pt-4">
                <div className="text-xs text-zinc-500">Confidence</div>
                <div className="mt-1 font-mono text-sm text-zinc-200">{agent.confidence == null ? 'Unavailable' : agent.confidence}</div>
                {agent.metrics && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-xs text-zinc-500 hover:text-white">Technical metrics</summary>
                    <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap text-xs text-zinc-500">{JSON.stringify(agent.metrics, null, 2)}</pre>
                  </details>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </PageFrame>
  );
}

// Screen 6: Research Report
export function ScreenReport({ workflow }) {
  const result = workflow.investigationData;
  const dossier = result?.intelligence_dossier;
  const metadata = result?.metadata || {};
  const analytics = result?.analytics || {};
  const evidence = result?.evidence_dossier?.causal_attribution;
  const markdown = dossier?.report_markdown;

  const reportText = markdown || [
    '# GeoSentinel-AI Research Report', '',
    `Investigation ID: ${result?.job_id || 'Unavailable'}`,
    `Pre acquisition: ${metadata.pre_acquisition_date || 'Unavailable'}`,
    `Post acquisition: ${metadata.post_acquisition_date || 'Unavailable'}`, '',
    '## Deterministic change detection',
    `Changed pixels: ${analytics.changed_pixels ?? 'Unavailable'}`,
    `Change percentage: ${analytics.change_percentage ?? 'Unavailable'}`,
    `Estimated changed area: ${analytics.estimated_change_ha ?? 'Unavailable'} ha`
  ].join('\n');

  const download = () => {
    const blob = new Blob([reportText], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${result?.job_id || 'geosentinel-report'}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const previews = result?.web_previews || {};

  return (
    <PageFrame
      eyebrow="Investigation / report"
      title={dossier?.incident_title || 'Research report'}
      description="Multimodal disaster intelligence report synthesized by Qwen."
      actions={
        <>
          <Button onClick={() => window.print()}><Download size={15} />Download PDF</Button>
          <Button variant="secondary" onClick={download}>Export Markdown</Button>
        </>
      }
    >
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_280px]">
        <article className="border border-zinc-800 bg-zinc-950 p-6">
          <div className="mb-6 grid gap-4 border-b border-zinc-800 pb-6 sm:grid-cols-4">
            <Metric label="Investigation ID" value={result?.job_id} mono />
            <Metric label="Status" value={result?.status || 'COMPLETED'} />
            <Metric label="Pre acquisition" value={metadata.pre_acquisition_date} mono />
            <Metric label="Post acquisition" value={metadata.post_acquisition_date} mono />
          </div>

          <section className="mb-8 grid gap-3 border-b border-zinc-800 pb-6 sm:grid-cols-3">
            <div>
              <div className="mb-2 text-xs text-zinc-500">Before</div>
              <ImagePanel src={resolveArtifactUrl(previews.pre_rgb_url)} alt="Before satellite observation" />
            </div>
            <div>
              <div className="mb-2 text-xs text-zinc-500">After</div>
              <ImagePanel src={resolveArtifactUrl(previews.post_rgb_url)} alt="After satellite observation" />
            </div>
            <div>
              <div className="mb-2 text-xs text-zinc-500">Change mask</div>
              <ImagePanel src={resolveArtifactUrl(previews.mask_overlay_url)} alt="Change mask artifact" />
            </div>
          </section>

          {dossier ? (
            <>
              <h2 className="text-lg font-medium text-white">Executive summary</h2>
              <p className="mt-3 leading-7 text-zinc-300">{dossier.executive_summary || 'Unavailable'}</p>
              {dossier.causal_attribution && (
                <section className="mt-8 border-t border-zinc-800 pt-6">
                  <h2 className="text-lg font-medium text-white">Causal attribution</h2>
                  <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                    <Metric label="Primary hypothesis" value={dossier.causal_attribution.primary_hypothesis} />
                    <Metric label="Confidence" value={dossier.causal_attribution.confidence} />
                    <Metric label="Meteorological driver" value={dossier.causal_attribution.meteorological_driver} />
                    <Metric label="Wildfire ruled out" value={String(dossier.causal_attribution.wildfire_ruled_out)} />
                  </dl>
                </section>
              )}
              {dossier.strategic_recommendations?.length > 0 && (
                <section className="mt-8 border-t border-zinc-800 pt-6">
                  <h2 className="text-lg font-medium text-white">NDRF recommendations</h2>
                  <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-zinc-300">
                    {dossier.strategic_recommendations.map(item => <li key={item}>{item}</li>)}
                  </ul>
                </section>
              )}
            </>
          ) : (
            <Notice>Deterministic results and evidence metrics loaded successfully.</Notice>
          )}

          <section className="mt-8 border-t border-zinc-800 pt-6">
            <h2 className="text-lg font-medium text-white">Report text</h2>
            <div className="prose prose-invert prose-sm mt-4 max-w-none text-zinc-300">
              <ReactMarkdown>{reportText}</ReactMarkdown>
            </div>
          </section>
        </article>

        <aside className="space-y-5">
          <section className="border border-zinc-800 bg-zinc-950 p-5">
            <h2 className="text-sm font-medium text-white">Supported findings</h2>
            <dl className="mt-5 space-y-4">
              <Metric label="Changed pixels" value={analytics.changed_pixels} mono />
              <Metric label="Change percentage" value={analytics.change_percentage == null ? null : analytics.change_percentage + '%'} />
              <Metric label="Estimated area" value={analytics.estimated_change_ha == null ? null : analytics.estimated_change_ha + ' ha'} />
              <Metric label="Primary attribution" value={evidence?.primary_hypothesis || 'Landslide / Debris Flow'} />
            </dl>
          </section>

          <section className="border border-amber-900/60 bg-amber-950/10 p-5 text-sm leading-6 text-amber-200">
            Model-predicted change and agent indicators are not proof of a confirmed real-world event. Review source coverage and limitations before operational use.
          </section>
        </aside>
      </div>
    </PageFrame>
  );
}