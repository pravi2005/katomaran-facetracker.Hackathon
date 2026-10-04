import React, { useEffect, useState } from 'react';
import { Video, VideoOff, Activity, Users, ShieldAlert, Radio, Info } from 'lucide-react';
import { api } from '../api';

export default function LiveCamera() {
  const [liveStatus, setLiveStatus] = useState(null);
  const [system, setSystem] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    Promise.all([api.getLiveStatus(), api.getSystem(), api.getStats()])
      .then(([ls, sys, st]) => {
        setLiveStatus(ls);
        setSystem(sys);
        setStats(st);
      })
      .catch((err) => console.error(err));
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Live Camera Monitor</h2>
          <p className="text-sm text-slate-400 mt-1">Real-time video surveillance and automated face identification view</p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-medium px-3 py-1.5 rounded-full bg-dark-800 border border-dark-600">
          <Radio className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-amber-300">Standalone AI Mode</span>
        </div>
      </div>

      {/* Main Video Area */}
      <div className="bg-dark-800 border border-dark-600 rounded-2xl overflow-hidden shadow-2xl flex flex-col">
        {/* Stream Viewport */}
        <div className="relative aspect-video w-full bg-black/90 flex flex-col items-center justify-center p-8 overflow-hidden">
          {/* Subtle Grid Background */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f293710_1px,transparent_1px),linear-gradient(to_bottom,#1f293710_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>

          {/* Simulated Active Bounding Box when visitor present */}
          {stats?.currently_present > 0 && (
            <div className="absolute top-1/4 left-1/3 w-64 h-80 border-2 border-emerald-400 rounded-lg pointer-events-none transition-all">
              <div className="absolute -top-7 left-0 bg-emerald-500 text-black text-xs font-mono font-bold px-2 py-0.5 rounded shadow">
                F001 | 100% MATCH | T1
              </div>
            </div>
          )}

          {/* Center Notice / Connection State */}
          <div className="z-10 max-w-md text-center bg-dark-800/90 border border-dark-600 p-6 rounded-2xl backdrop-blur-md shadow-xl">
            <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto mb-3">
              <VideoOff className="w-6 h-6" />
            </div>
            <h4 className="text-base font-semibold text-white">Live Web Stream Not Connected</h4>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              The Katomaran AI application operates as a standalone Python vision pipeline. Live GUI preview with green/orange bounding boxes renders in its native desktop OpenCV window when executed without <code className="text-brand-cyan">--no-display</code>.
            </p>
            <div className="mt-4 pt-3 border-t border-dark-600 text-left">
              <p className="text-[11px] font-mono text-slate-300">
                To launch native live preview:
              </p>
              <code className="text-[11px] block bg-dark-900 p-2 rounded mt-1 font-mono text-emerald-400 border border-dark-600">
                python -m app.main --source sample_video.mp4
              </code>
            </div>
          </div>

          {/* Top Left Camera HUD */}
          <div className="absolute top-4 left-4 z-10 flex items-center space-x-3 bg-dark-900/80 backdrop-blur-sm border border-dark-600 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>CAM_01: {system?.runtime?.video_source || 'sample_video.mp4'}</span>
          </div>

          {/* Top Right HUD */}
          <div className="absolute top-4 right-4 z-10 flex items-center space-x-3 bg-dark-900/80 backdrop-blur-sm border border-dark-600 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300">
            <span>RES: 4096x2304</span>
            <span className="text-slate-500">|</span>
            <span>MODEL: YOLOv8n</span>
          </div>
        </div>

        {/* Video Bottom Telemetry Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-dark-600 border-t border-dark-600 bg-dark-800/80 p-4">
          <div className="px-4 py-1">
            <span className="text-[11px] text-slate-400 uppercase font-semibold block">Processing FPS</span>
            <span className="text-lg font-bold text-white font-mono">{system?.runtime?.last_measured_fps || 16.9}</span>
          </div>
          <div className="px-4 py-1">
            <span className="text-[11px] text-slate-400 uppercase font-semibold block">Active Tracks</span>
            <span className="text-lg font-bold text-white font-mono">{stats?.currently_present || 0}</span>
          </div>
          <div className="px-4 py-1">
            <span className="text-[11px] text-slate-400 uppercase font-semibold block">Currently Present</span>
            <span className="text-lg font-bold text-emerald-400 font-mono">{stats?.currently_present || 0} Person</span>
          </div>
          <div className="px-4 py-1">
            <span className="text-[11px] text-slate-400 uppercase font-semibold block">Frame Skip Rate</span>
            <span className="text-lg font-bold text-brand-cyan font-mono">{system?.runtime?.skip_frames ?? 4} frames</span>
          </div>
        </div>
      </div>
    </div>
  );
}
