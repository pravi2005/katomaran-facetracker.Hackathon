import React, { useEffect, useState } from 'react';
import { History, Filter, Search, ArrowDownRight, ArrowUpRight } from 'lucide-react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';

export default function Events() {
  const [events, setEvents] = useState([]);
  const [filterType, setFilterType] = useState('');
  const [searchFace, setSearchFace] = useState('');
  const [loading, setLoading] = useState(true);

  const loadEvents = () => {
    setLoading(true);
    api.getEvents(100, filterType, searchFace)
      .then(setEvents)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadEvents();
  }, [filterType, searchFace]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Event Timeline</h2>
          <p className="text-sm text-slate-400 mt-1">Audit log of all detected ENTRY and EXIT transitions in SQLite</p>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-3">
          {/* Type Filter Buttons */}
          <div className="flex bg-dark-800 p-1 rounded-xl border border-dark-600">
            <button
              onClick={() => setFilterType('')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                filterType === '' ? 'bg-dark-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterType('ENTRY')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                filterType === 'ENTRY' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              ENTRY
            </button>
            <button
              onClick={() => setFilterType('EXIT')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                filterType === 'EXIT' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              EXIT
            </button>
          </div>

          {/* Search Face */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter Face ID..."
              value={searchFace}
              onChange={(e) => setSearchFace(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-xl bg-dark-800 border border-dark-600 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-blue transition w-36"
            />
          </div>
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-dark-800 border border-dark-600 rounded-2xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-16 text-center text-slate-400">Loading events...</div>
        ) : events.length === 0 ? (
          <div className="py-16 text-center text-slate-400">
            <History className="w-10 h-10 text-slate-500 mx-auto mb-2" />
            <p className="text-sm font-medium">No events match the selected filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-dark-600 bg-dark-800/80 text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                  <th className="py-3.5 px-6">Timestamp</th>
                  <th className="py-3.5 px-6">Video Time</th>
                  <th className="py-3.5 px-6">Face ID</th>
                  <th className="py-3.5 px-6">Event</th>
                  <th className="py-3.5 px-6">Reason</th>
                  <th className="py-3.5 px-6">Track ID</th>
                  <th className="py-3.5 px-6 text-right">Face Crop</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-600">
                {events.map((ev) => (
                  <tr key={ev.event_id} className="hover:bg-dark-700/40 transition">
                    <td className="py-4 px-6 text-xs text-slate-300 font-mono">
                      {new Date(ev.timestamp).toLocaleString()}
                    </td>
                    <td className="py-4 px-6 text-xs text-brand-cyan font-mono">
                      {ev.source_timestamp}
                    </td>
                    <td className="py-4 px-6 font-mono font-bold text-white">
                      {ev.face_id}
                    </td>
                    <td className="py-4 px-6">
                      <StatusBadge type="event" value={ev.event_type} />
                    </td>
                    <td className="py-4 px-6 text-xs text-slate-400 font-mono">
                      {ev.reason || '—'}
                    </td>
                    <td className="py-4 px-6 text-xs text-slate-400 font-mono">
                      #{ev.track_id}
                    </td>
                    <td className="py-4 px-6 text-right">
                      {ev.image_path ? (
                        <img
                          src={api.getImageUrl(ev.image_path)}
                          alt={`${ev.face_id} crop`}
                          className="w-10 h-10 rounded-lg object-cover border border-dark-500 inline-block shadow-sm"
                        />
                      ) : (
                        <span className="text-xs text-slate-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
