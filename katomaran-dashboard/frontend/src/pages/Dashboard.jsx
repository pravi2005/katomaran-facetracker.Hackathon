import React, { useEffect, useState } from 'react';
import { Users, UserCheck, ArrowDownRight, ArrowUpRight, Activity, Cpu, Database, Eye, RefreshCw } from 'lucide-react';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import { api } from '../api';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [system, setSystem] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);
  const [presence, setPresence] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [s, sys, evs, pres] = await Promise.all([
        api.getStats(),
        api.getSystem(),
        api.getEvents(5),
        api.getPresence(),
      ]);
      setStats(s);
      setSystem(sys);
      setRecentEvents(evs);
      setPresence(pres);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // 5-second polling
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Title & Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">System Overview</h2>
          <p className="text-sm text-slate-400 mt-1">Live metrics from Katomaran AI runtime and SQLite store</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-medium bg-dark-800 border border-dark-600 hover:border-dark-500 text-slate-300 hover:text-white transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Currently Present"
          value={stats ? stats.currently_present : '-'}
          subtitle={stats?.currently_present > 0 ? `${stats.currently_present} visitor(s) active on camera` : 'No active visitors currently'}
          icon={Eye}
          color="emerald"
        />
        <StatCard
          title="Unique Visitors"
          value={stats ? stats.unique_visitors : '-'}
          subtitle="Total unique identities registered"
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Entries Today"
          value={stats ? stats.entries_today : '-'}
          subtitle={`Total all-time entries: ${stats?.entries_total ?? 0}`}
          icon={ArrowDownRight}
          color="cyan"
        />
        <StatCard
          title="Exits Today"
          value={stats ? stats.exits_today : '-'}
          subtitle={`Total all-time exits: ${stats?.exits_total ?? 0}`}
          icon={ArrowUpRight}
          color="amber"
        />
      </div>

      {/* Pipeline Status Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 p-5 rounded-2xl bg-dark-800 border border-dark-600">
        <div className="flex items-center space-x-3 p-3 rounded-xl bg-dark-700/50">
          <Activity className="w-5 h-5 text-brand-blue" />
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">YOLO Face Detection</span>
            <span className="text-sm font-semibold text-emerald-400">● {system?.yolo?.status || 'READY'}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3 p-3 rounded-xl bg-dark-700/50">
          <UserCheck className="w-5 h-5 text-brand-cyan" />
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">InsightFace 512-d</span>
            <span className="text-sm font-semibold text-emerald-400">● {system?.insightface?.status || 'READY'}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3 p-3 rounded-xl bg-dark-700/50">
          <Database className="w-5 h-5 text-brand-purple" />
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">SQLite Database</span>
            <span className="text-sm font-semibold text-emerald-400">● {system?.database?.status || 'CONNECTED'}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3 p-3 rounded-xl bg-dark-700/50">
          <Cpu className="w-5 h-5 text-brand-orange" />
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Execution Provider</span>
            <span className="text-sm font-semibold text-slate-200">{system?.runtime?.execution_device || 'CPU'} (ONNX)</span>
          </div>
        </div>

        <div className="flex items-center space-x-3 p-3 rounded-xl bg-dark-700/50">
          <Activity className="w-5 h-5 text-emerald-400" />
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Processing Speed</span>
            <span className="text-sm font-semibold text-slate-200">~{system?.runtime?.last_measured_fps || 16.9} FPS</span>
          </div>
        </div>
      </div>

      {/* Main Content Split: Currently Present & Recent Events */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Currently Present Card */}
        <div className="bg-dark-800 border border-dark-600 rounded-2xl p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-white flex items-center">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 mr-2.5 animate-pulse"></span>
              Live Presence
            </h3>
            <span className="text-xs font-mono text-slate-400 bg-dark-700 px-2 py-0.5 rounded">
              {presence.length} active
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3">
            {presence.length === 0 ? (
              <div className="h-44 flex flex-col items-center justify-center text-center p-4 border border-dashed border-dark-600 rounded-xl">
                <Users className="w-8 h-8 text-slate-500 mb-2" />
                <p className="text-xs text-slate-400">No visitors currently inside</p>
                <p className="text-[11px] text-slate-500 mt-1">Status changes when a new face enters</p>
              </div>
            ) : (
              presence.map((p) => (
                <div key={p.event_id} className="flex items-center justify-between p-3 rounded-xl bg-dark-700/60 border border-dark-600">
                  <div className="flex items-center space-x-3">
                    {p.representative_image_path ? (
                      <img
                        src={api.getImageUrl(p.representative_image_path)}
                        alt={p.face_id}
                        className="w-10 h-10 rounded-lg object-cover border border-dark-500"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-lg bg-dark-600 flex items-center justify-center">
                        <Users className="w-5 h-5 text-slate-400" />
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-bold text-white font-mono">{p.face_id}</p>
                      <p className="text-[11px] text-slate-400">In since {new Date(p.timestamp).toLocaleTimeString()}</p>
                    </div>
                  </div>
                  <StatusBadge type="presence" value="Present" />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Events Timeline */}
        <div className="lg:col-span-2 bg-dark-800 border border-dark-600 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-white">Recent Presence Events</h3>
            <span className="text-xs text-slate-400 font-medium">Last 5 records from SQLite</span>
          </div>

          {recentEvents.length === 0 ? (
            <div className="h-44 flex flex-col items-center justify-center text-center p-4 border border-dashed border-dark-600 rounded-xl">
              <p className="text-xs text-slate-400">No events logged yet</p>
            </div>
          ) : (
            <div className="divide-y divide-dark-600">
              {recentEvents.map((ev) => (
                <div key={ev.event_id} className="py-3.5 flex items-center justify-between first:pt-0 last:pb-0">
                  <div className="flex items-center space-x-4">
                    <StatusBadge type="event" value={ev.event_type} />
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-white font-mono">{ev.face_id}</span>
                        {ev.reason && (
                          <span className="text-[11px] px-1.5 py-0.5 rounded bg-dark-700 text-slate-400 font-mono">
                            {ev.reason}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {new Date(ev.timestamp).toLocaleTimeString()} ({ev.source_timestamp}) • Track #{ev.track_id}
                      </p>
                    </div>
                  </div>

                  {ev.image_path && (
                    <img
                      src={api.getImageUrl(ev.image_path)}
                      alt={`${ev.face_id}`}
                      className="w-10 h-10 rounded-lg object-cover border border-dark-500 shadow-sm"
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
