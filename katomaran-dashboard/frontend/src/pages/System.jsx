import React, { useEffect, useState } from 'react';
import { Server, Database, Activity, Cpu, Sliders, HardDrive, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';

export default function System() {
  const [system, setSystem] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSystem()
      .then(setSystem)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="py-20 text-center text-slate-400">Loading system status...</div>;
  }

  const { database, yolo, insightface, runtime } = system || {};

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">System Diagnostics</h2>
        <p className="text-sm text-slate-400 mt-1">Operational state of machine learning models, database, and hardware providers</p>
      </div>

      {/* Main Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Core Services Card */}
        <div className="bg-dark-800 border border-dark-600 rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-3 text-white mb-2">
            <Activity className="w-5 h-5 text-brand-blue" />
            <h3 className="font-semibold text-base">Service Status</h3>
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between p-2.5 rounded-xl bg-dark-700/50">
              <span className="text-slate-300">AI Pipeline</span>
              <StatusBadge type="system" value={system?.pipeline_status || 'ONLINE'} />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-dark-700/50">
              <span className="text-slate-300">YOLO Face Detector</span>
              <StatusBadge type="system" value={yolo?.status || 'READY'} />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-dark-700/50">
              <span className="text-slate-300">InsightFace Embedder</span>
              <StatusBadge type="system" value={insightface?.status || 'READY'} />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-dark-700/50">
              <span className="text-slate-300">SQLite Repository</span>
              <StatusBadge type="system" value={database?.status || 'CONNECTED'} />
            </div>
          </div>
        </div>

        {/* AI Model Stack */}
        <div className="bg-dark-800 border border-dark-600 rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-3 text-white mb-2">
            <Cpu className="w-5 h-5 text-brand-cyan" />
            <h3 className="font-semibold text-base">Inference Runtime</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded-xl bg-dark-700/50 space-y-1">
              <span className="text-slate-400 font-semibold uppercase block">Execution Device</span>
              <span className="text-sm font-bold text-white font-mono">{runtime?.execution_device} (ONNX Runtime)</span>
            </div>

            <div className="p-3 rounded-xl bg-dark-700/50 space-y-1">
              <span className="text-slate-400 font-semibold uppercase block">InsightFace Pack</span>
              <span className="text-sm font-bold text-emerald-400 font-mono">{insightface?.model_pack}</span>
              <p className="text-[11px] text-slate-400">Embedding Dim: {insightface?.embedding_dimension} dimensions</p>
            </div>

            <div className="p-3 rounded-xl bg-dark-700/50 space-y-1">
              <span className="text-slate-400 font-semibold uppercase block">Measured Performance</span>
              <span className="text-sm font-bold text-white font-mono">~{runtime?.last_measured_fps} FPS (CPU benchmark)</span>
            </div>
          </div>
        </div>

        {/* Database & Storage */}
        <div className="bg-dark-800 border border-dark-600 rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-3 text-white mb-2">
            <Database className="w-5 h-5 text-brand-purple" />
            <h3 className="font-semibold text-base">Persistence & Logs</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded-xl bg-dark-700/50 space-y-1">
              <span className="text-slate-400 font-semibold uppercase block">Database File</span>
              <span className="text-xs font-mono text-slate-200 block truncate">{database?.path}</span>
              <p className="text-[11px] text-slate-400">Schema Version: v{database?.schema_version} | Size: {(database?.size_bytes / 1024).toFixed(1)} KB</p>
            </div>

            <div className="p-3 rounded-xl bg-dark-700/50 space-y-1">
              <span className="text-slate-400 font-semibold uppercase block">Audit Event Log</span>
              <span className="text-xs font-mono text-emerald-400">{runtime?.events_log}</span>
              <p className="text-[11px] text-slate-400">Path: logs/events.log</p>
            </div>

            <div className="p-3 rounded-xl bg-dark-700/50 space-y-1">
              <span className="text-slate-400 font-semibold uppercase block">Counting Scope</span>
              <span className="text-xs font-mono text-white capitalize">{runtime?.counting_scope}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration Table */}
      <div className="bg-dark-800 border border-dark-600 rounded-2xl p-6">
        <h3 className="text-base font-semibold text-white mb-4 flex items-center">
          <Sliders className="w-4 h-4 mr-2 text-brand-orange" />
          Active Configuration Parameters (config.json)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-xl bg-dark-700/40 border border-dark-600">
            <span className="text-slate-400 block mb-1">detection.skip_frames</span>
            <span className="text-sm font-bold text-white">{runtime?.skip_frames}</span>
          </div>

          <div className="p-3 rounded-xl bg-dark-700/40 border border-dark-600">
            <span className="text-slate-400 block mb-1">similarity_threshold</span>
            <span className="text-sm font-bold text-brand-cyan">{runtime?.similarity_threshold}</span>
          </div>

          <div className="p-3 rounded-xl bg-dark-700/40 border border-dark-600">
            <span className="text-slate-400 block mb-1">max_missing_seconds</span>
            <span className="text-sm font-bold text-white">{runtime?.max_missing_seconds}s</span>
          </div>

          <div className="p-3 rounded-xl bg-dark-700/40 border border-dark-600">
            <span className="text-slate-400 block mb-1">input.source</span>
            <span className="text-sm font-bold text-white truncate block">{runtime?.video_source}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
