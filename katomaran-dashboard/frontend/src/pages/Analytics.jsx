import React, { useEffect, useState } from 'react';
import { BarChart3, PieChart, Users, TrendingUp, Calendar } from 'lucide-react';
import { api } from '../api';

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAnalytics()
      .then(setData)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="py-20 text-center text-slate-400">Loading analytics...</div>;
  }

  if (!data || !data.has_data) {
    return (
      <div className="py-24 text-center">
        <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-300">No historical data available yet</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          Process video streams to accumulate entry/exit transitions and visitor frequency statistics.
        </p>
      </div>
    );
  }

  const { event_breakdown, visits_per_person, timeline, total_events } = data;
  const entryPct = total_events > 0 ? Math.round((event_breakdown.ENTRY / total_events) * 100) : 0;
  const exitPct = total_events > 0 ? 100 - entryPct : 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Visual Analytics</h2>
        <p className="text-sm text-slate-400 mt-1">Aggregated visitor flow patterns and frequency metrics</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Event Ratio Card */}
        <div className="bg-dark-800 border border-dark-600 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-base font-semibold text-white flex items-center">
              <PieChart className="w-4 h-4 mr-2 text-brand-blue" />
              Transition Distribution
            </h3>
            <span className="text-xs font-mono text-slate-400">Total: {total_events} events</span>
          </div>

          {/* Progress Bar */}
          <div className="h-4 w-full bg-dark-700 rounded-full overflow-hidden flex mb-6">
            <div
              style={{ width: `${entryPct}%` }}
              className="bg-emerald-500 transition-all duration-500 relative group"
            />
            <div
              style={{ width: `${exitPct}%` }}
              className="bg-amber-500 transition-all duration-500 relative group"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-dark-700/50 border border-dark-600">
              <div className="flex items-center space-x-2 mb-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                <span className="text-xs font-semibold uppercase text-slate-400">Entries</span>
              </div>
              <span className="text-2xl font-bold text-white">{event_breakdown.ENTRY}</span>
              <span className="text-xs text-slate-400 ml-2">({entryPct}%)</span>
            </div>

            <div className="p-4 rounded-xl bg-dark-700/50 border border-dark-600">
              <div className="flex items-center space-x-2 mb-1">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                <span className="text-xs font-semibold uppercase text-slate-400">Exits</span>
              </div>
              <span className="text-2xl font-bold text-white">{event_breakdown.EXIT}</span>
              <span className="text-xs text-slate-400 ml-2">({exitPct}%)</span>
            </div>
          </div>
        </div>

        {/* Top Visitors Frequency */}
        <div className="bg-dark-800 border border-dark-600 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-base font-semibold text-white flex items-center">
              <Users className="w-4 h-4 mr-2 text-brand-cyan" />
              Visit Frequency by Identity
            </h3>
            <span className="text-xs font-mono text-slate-400">Top Individuals</span>
          </div>

          <div className="space-y-4">
            {visits_per_person.map((item, idx) => {
              const maxCount = Math.max(...visits_per_person.map((v) => v.count), 1);
              const barWidth = Math.round((item.count / maxCount) * 100);

              return (
                <div key={item.face_id} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-bold text-white">{item.face_id}</span>
                    <span className="text-slate-400 font-mono">{item.count} visit{item.count > 1 ? 's' : ''}</span>
                  </div>
                  <div className="h-2 w-full bg-dark-700 rounded-full overflow-hidden">
                    <div
                      style={{ width: `${barWidth}%` }}
                      className="h-full bg-brand-cyan rounded-full transition-all duration-500"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
