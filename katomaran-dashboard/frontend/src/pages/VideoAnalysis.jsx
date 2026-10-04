import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Upload, Film, Play, CheckCircle2, XCircle, Loader2,
  Users, ArrowRightLeft, Clock, Eye, BarChart3, AlertTriangle,
  ChevronDown, ChevronUp, RefreshCw,
} from 'lucide-react';
import { api } from '../api';

const ALLOWED = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
const POLL_MS = 2000;

function fmtBytes(b) {
  if (!b) return '—';
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtTs(ts) {
  if (!ts) return '—';
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

function StatusBadge({ status }) {
  const map = {
    pending:   { bg: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400', label: 'Pending' },
    running:   { bg: 'bg-blue-500/10 border-blue-500/30 text-blue-400', label: 'Processing' },
    completed: { bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400', label: 'Completed' },
    failed:    { bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400', label: 'Failed' },
  };
  const s = map[status] || map.pending;
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${s.bg}`}>
      {s.label}
    </span>
  );
}

function StatTile({ label, value, accent }) {
  return (
    <div className="bg-dark-800 border border-dark-600 rounded-xl p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent || 'text-white'}`}>{value ?? '—'}</p>
    </div>
  );
}

// ── Upload & Analyze Panel ────────────────────────────────────────────────────
function UploadPanel({ onAnalysisStarted }) {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef();

  const pick = (f) => {
    setError('');
    if (!f) return;
    const ext = '.' + f.name.split('.').pop().toLowerCase();
    if (!ALLOWED.includes(ext)) {
      setError(`Unsupported format: ${ext}. Accepted: ${ALLOWED.join(', ')}`);
      return;
    }
    setFile(f);
  };

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    pick(e.dataTransfer.files[0]);
  };

  const analyze = async () => {
    if (!file) return;
    setUploading(true); setError('');
    try {
      const res = await api.uploadAndAnalyze(file);
      onAnalysisStarted(res.analysis_id);
    } catch (e) {
      setError(e.message || 'Upload failed.');
      setUploading(false);
    }
  };

  return (
    <div className="max-w-xl">
      <h2 className="text-xl font-bold text-white mb-1">Upload Video</h2>
      <p className="text-sm text-slate-400 mb-6">
        The existing YOLO + InsightFace pipeline will process your video and generate a full analysis report.
      </p>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center cursor-pointer transition-all
          ${dragOver ? 'border-brand-blue bg-brand-blue/10' : 'border-dark-500 hover:border-dark-400 hover:bg-dark-800/60'}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED.join(',')}
          className="hidden"
          onChange={(e) => pick(e.target.files[0])}
        />
        <Film className="w-10 h-10 text-slate-500 mb-3" />
        {file ? (
          <>
            <p className="text-white font-semibold">{file.name}</p>
            <p className="text-sm text-slate-400 mt-1">{fmtBytes(file.size)}</p>
          </>
        ) : (
          <>
            <p className="text-slate-300 font-medium">Drop a video here or click to browse</p>
            <p className="text-xs text-slate-500 mt-1">Accepted: MP4, AVI, MOV, MKV, WEBM</p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-3 flex items-start gap-2 text-rose-400 text-sm bg-rose-500/10 border border-rose-500/20 rounded-xl p-3">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <button
        onClick={analyze}
        disabled={!file || uploading}
        className="mt-5 w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-all
          bg-brand-blue hover:bg-brand-blue/80 text-white disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {uploading ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</> : <><Play className="w-4 h-4" /> Analyze Video</>}
      </button>
    </div>
  );
}

// ── Processing Progress ───────────────────────────────────────────────────────
function ProcessingPanel({ analysisId, onComplete }) {
  const [status, setStatus] = useState('pending');
  const [error, setError] = useState('');
  const timerRef = useRef(null);

  const poll = useCallback(async () => {
    try {
      const data = await api.getAnalysisStatus(analysisId);
      setStatus(data.status);
      if (data.status === 'completed') { onComplete(); return; }
      if (data.status === 'failed') { setError(data.error || 'Processing failed.'); return; }
      timerRef.current = setTimeout(poll, POLL_MS);
    } catch (e) {
      setError(e.message);
    }
  }, [analysisId, onComplete]);

  useEffect(() => {
    poll();
    return () => clearTimeout(timerRef.current);
  }, [poll]);

  const steps = [
    'Initialising models…',
    'Detecting faces (YOLO)…',
    'Tracking identities (ByteTrack)…',
    'Recognising faces (InsightFace / ArcFace)…',
    'Recording presence events…',
    'Finalising report…',
  ];

  if (status === 'failed') {
    return (
      <div className="max-w-xl">
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-6 flex items-start gap-3">
          <XCircle className="w-6 h-6 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-rose-300 mb-1">Processing Failed</p>
            <p className="text-sm text-rose-400/80 font-mono whitespace-pre-wrap">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl">
      <div className="bg-dark-800 border border-dark-600 rounded-2xl p-7">
        <div className="flex items-center gap-3 mb-6">
          <Loader2 className="w-6 h-6 text-brand-blue animate-spin" />
          <div>
            <p className="font-bold text-white">Processing Video</p>
            <p className="text-xs text-slate-400">Analysis ID: {analysisId}</p>
          </div>
          <StatusBadge status={status} />
        </div>

        {/* Indeterminate progress bar */}
        <div className="h-1.5 bg-dark-600 rounded-full overflow-hidden mb-6">
          <div className="h-full bg-gradient-to-r from-brand-blue to-brand-cyan rounded-full animate-[slide_2s_linear_infinite] w-1/3" />
        </div>

        <div className="space-y-2.5">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-2.5 text-sm text-slate-400">
              <div className="w-1.5 h-1.5 rounded-full bg-dark-500 flex-shrink-0" />
              <span>{s}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-500 mt-5">
          CPU inference — processing time depends on video length. Please wait.
        </p>
      </div>
    </div>
  );
}

// ── Report Display ────────────────────────────────────────────────────────────
function ReportPanel({ analysisId, onAnalyzeAnother }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const [showEvents, setShowEvents] = useState(false);

  useEffect(() => {
    api.getAnalysisReport(analysisId)
      .then(setReport)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [analysisId]);

  if (loading) return <div className="flex gap-2 text-slate-400"><Loader2 className="animate-spin w-5 h-5" /> Loading report…</div>;
  if (err) return <div className="text-rose-400">{err}</div>;
  if (!report) return null;

  const m = report.metrics || {};
  const s = report.summary || {};

  const fps = m.avg_fps ?? null;
  const framesProcessed = m.frames_processed ?? '—';
  const uniqueVisitors = s.unique_visitors ?? m.unique_visitors ?? '—';
  const entryEvents = s.entry_events ?? '—';
  const exitEvents = s.exit_events ?? '—';
  const facesRegistered = m.faces_registered ?? '—';
  const processingTime = m.processing_seconds ? `${m.processing_seconds}s` : '—';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            <h2 className="text-xl font-bold text-white">Analysis Report</h2>
            <StatusBadge status={report.status} />
          </div>
          <p className="text-sm text-slate-400">
            {report.filename} &nbsp;·&nbsp; ID: {analysisId}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">
            Started: {fmtTs(report.started_at)} &nbsp;·&nbsp; Finished: {fmtTs(report.finished_at)}
          </p>
        </div>
        <button
          onClick={onAnalyzeAnother}
          className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-xl bg-dark-700 border border-dark-500 text-slate-300 hover:text-white transition"
        >
          <RefreshCw className="w-4 h-4" /> Analyze Another
        </button>
      </div>

      {/* Summary Stats Grid */}
      <div>
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatTile label="Frames Processed" value={framesProcessed} />
          <StatTile label="Avg FPS" value={fps !== null ? fps.toFixed(1) : '—'} accent="text-brand-cyan" />
          <StatTile label="Unique Visitors" value={uniqueVisitors} accent="text-brand-blue" />
          <StatTile label="Faces Registered" value={facesRegistered} />
          <StatTile label="ENTRY Events" value={entryEvents} accent="text-emerald-400" />
          <StatTile label="EXIT Events" value={exitEvents} accent="text-rose-400" />
          <StatTile label="Processing Time" value={processingTime} />
          <StatTile label="Analysis ID" value={analysisId} />
        </div>
      </div>

      {/* Visitor Report */}
      {report.visitors?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
            <Users className="inline w-4 h-4 mr-1" />Visitor Report
          </h3>
          <div className="bg-dark-800 border border-dark-600 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-600 text-xs text-slate-500 uppercase tracking-wider">
                  <th className="text-left px-4 py-3">Face ID</th>
                  <th className="text-left px-4 py-3">Registered</th>
                  <th className="text-left px-4 py-3">First Seen</th>
                  <th className="text-left px-4 py-3">Last Seen</th>
                  <th className="text-right px-4 py-3">Visits</th>
                </tr>
              </thead>
              <tbody>
                {report.visitors.map((v) => (
                  <tr key={v.face_id} className="border-b border-dark-700/50 hover:bg-dark-700/30 transition">
                    <td className="px-4 py-3 font-mono text-brand-cyan font-semibold">{v.face_id}</td>
                    <td className="px-4 py-3 text-slate-400">{fmtTs(v.registered_at)}</td>
                    <td className="px-4 py-3 text-slate-400">{fmtTs(v.first_seen)}</td>
                    <td className="px-4 py-3 text-slate-400">{fmtTs(v.last_seen)}</td>
                    <td className="px-4 py-3 text-right text-white font-semibold">{v.visit_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Event Timeline */}
      {report.events?.length > 0 && (
        <div>
          <button
            onClick={() => setShowEvents((p) => !p)}
            className="flex items-center gap-2 text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3 hover:text-white transition"
          >
            <ArrowRightLeft className="w-4 h-4" />
            Event Timeline ({report.events.length} events)
            {showEvents ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {showEvents && (
            <div className="bg-dark-800 border border-dark-600 rounded-xl overflow-hidden max-h-96 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-dark-800">
                  <tr className="border-b border-dark-600 text-xs text-slate-500 uppercase tracking-wider">
                    <th className="text-left px-4 py-3">Time</th>
                    <th className="text-left px-4 py-3">Face ID</th>
                    <th className="text-left px-4 py-3">Event</th>
                    <th className="text-left px-4 py-3">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {report.events.map((e) => (
                    <tr key={e.event_id} className="border-b border-dark-700/50 hover:bg-dark-700/30">
                      <td className="px-4 py-2.5 text-slate-400 font-mono text-xs">{fmtTs(e.timestamp)}</td>
                      <td className="px-4 py-2.5 font-mono text-brand-cyan font-semibold">{e.face_id}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
                          e.event_type === 'ENTRY'
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                            : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                        }`}>{e.event_type}</span>
                      </td>
                      <td className="px-4 py-2.5 text-slate-500 text-xs">{e.reason || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Face Registrations */}
      {report.registrations?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
            <Eye className="inline w-4 h-4 mr-1" />Detected Faces ({report.registrations.length})
          </h3>
          <div className="flex flex-wrap gap-4">
            {report.registrations.map((r) => (
              <div key={r.face_id} className="bg-dark-800 border border-dark-600 rounded-xl p-3 flex flex-col items-center gap-2 w-28">
                {r.representative_image_path ? (
                  <img
                    src={api.getImageUrl(r.representative_image_path.replace(/\\/g, '/').replace(/.*logs\//, ''))}
                    alt={r.face_id}
                    className="w-16 h-16 rounded-lg object-cover bg-dark-700"
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                ) : (
                  <div className="w-16 h-16 rounded-lg bg-dark-700 flex items-center justify-center">
                    <Users className="w-6 h-6 text-slate-600" />
                  </div>
                )}
                <span className="text-xs font-mono text-brand-cyan font-semibold">{r.face_id}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing Info */}
      <div>
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
          <BarChart3 className="inline w-4 h-4 mr-1" />Processing Information
        </h3>
        <div className="bg-dark-800 border border-dark-600 rounded-xl p-5 grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          {[
            ['Detector', 'YOLO v8n-face'],
            ['Recogniser', 'InsightFace / ArcFace'],
            ['Tracker', 'ByteTrack-style'],
            ['Inference', 'CPU (ONNX Runtime)'],
            ['Embeddings', '512-dimensional'],
            ['Processing Time', processingTime],
          ].map(([k, v]) => (
            <div key={k}>
              <p className="text-xs text-slate-500 mb-0.5">{k}</p>
              <p className="text-white font-medium">{v}</p>
            </div>
          ))}
        </div>
      </div>

      {/* No faces warning */}
      {report.visitors?.length === 0 && report.status === 'completed' && (
        <div className="flex items-start gap-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 text-yellow-400 text-sm">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">No faces detected</p>
            <p className="text-yellow-400/70 mt-0.5">
              The video was processed but no faces passed the quality gate. Try a video with clearer, larger face crops.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── History Sidebar ───────────────────────────────────────────────────────────
function HistorySidebar({ onSelect }) {
  const [analyses, setAnalyses] = useState([]);

  useEffect(() => {
    api.listAnalyses().then(setAnalyses).catch(() => {});
    const t = setInterval(() => api.listAnalyses().then(setAnalyses).catch(() => {}), 5000);
    return () => clearInterval(t);
  }, []);

  if (!analyses.length) return null;

  return (
    <div className="w-56 flex-shrink-0">
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Past Analyses</p>
      <div className="space-y-2">
        {analyses.map((a) => (
          <button
            key={a.analysis_id}
            onClick={() => onSelect(a)}
            className="w-full text-left bg-dark-800 border border-dark-600 rounded-xl p-3 hover:border-dark-400 transition"
          >
            <p className="text-xs font-mono text-brand-cyan font-semibold">{a.analysis_id}</p>
            <p className="text-xs text-slate-400 truncate mt-0.5">{a.filename}</p>
            <div className="mt-1.5"><StatusBadge status={a.status} /></div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function VideoAnalysis() {
  // stage: 'upload' | 'processing' | 'report'
  const [stage, setStage] = useState('upload');
  const [analysisId, setAnalysisId] = useState(null);

  const handleStarted = (id) => { setAnalysisId(id); setStage('processing'); };
  const handleComplete = () => setStage('report');
  const handleAnother = () => { setAnalysisId(null); setStage('upload'); };
  const handleHistorySelect = (a) => {
    setAnalysisId(a.analysis_id);
    if (a.status === 'completed' || a.status === 'failed') setStage('report');
    else if (a.status === 'running' || a.status === 'pending') setStage('processing');
    else setStage('report');
  };

  return (
    <div>
      {/* Page title */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-600 to-brand-blue flex items-center justify-center">
            <Upload className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Video Analysis</h1>
            <p className="text-sm text-slate-400">Upload a video · Run the AI pipeline · Get the full report</p>
          </div>
        </div>
      </div>

      <div className="flex gap-8">
        {/* Main content */}
        <div className="flex-1 min-w-0">
          {stage === 'upload' && <UploadPanel onAnalysisStarted={handleStarted} />}
          {stage === 'processing' && <ProcessingPanel analysisId={analysisId} onComplete={handleComplete} />}
          {stage === 'report' && <ReportPanel analysisId={analysisId} onAnalyzeAnother={handleAnother} />}
        </div>

        {/* History */}
        <HistorySidebar onSelect={handleHistorySelect} />
      </div>
    </div>
  );
}
