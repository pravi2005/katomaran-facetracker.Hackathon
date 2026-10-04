import React, { useEffect, useState } from 'react';
import { Users, Search, ChevronRight, User } from 'lucide-react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';
import VisitorModal from '../components/VisitorModal';

export default function Visitors() {
  const [visitors, setVisitors] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedFaceId, setSelectedFaceId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getVisitors()
      .then(setVisitors)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const filtered = visitors.filter((v) =>
    v.face_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Visitors Registry</h2>
          <p className="text-sm text-slate-400 mt-1">Unique individuals recognized and tracked across video sessions</p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search Face ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-xl bg-dark-800 border border-dark-600 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-blue transition w-full sm:w-64"
          />
        </div>
      </div>

      {/* Visitors Table */}
      <div className="bg-dark-800 border border-dark-600 rounded-2xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-16 text-center text-slate-400">Loading visitors...</div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-slate-400">
            <Users className="w-10 h-10 text-slate-500 mx-auto mb-2" />
            <p className="text-sm font-medium">No visitors found</p>
            <p className="text-xs text-slate-500 mt-1">Visitors appear here after automatic detection and registration</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-dark-600 bg-dark-800/80 text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                  <th className="py-3.5 px-6">Face</th>
                  <th className="py-3.5 px-6">Face ID</th>
                  <th className="py-3.5 px-6">Current Status</th>
                  <th className="py-3.5 px-6">First Seen</th>
                  <th className="py-3.5 px-6">Last Seen</th>
                  <th className="py-3.5 px-6 text-center">Visits</th>
                  <th className="py-3.5 px-6 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-600">
                {filtered.map((v) => (
                  <tr
                    key={v.face_id}
                    onClick={() => setSelectedFaceId(v.face_id)}
                    className="hover:bg-dark-700/40 transition cursor-pointer group"
                  >
                    <td className="py-4 px-6">
                      {v.representative_image_path ? (
                        <img
                          src={api.getImageUrl(v.representative_image_path)}
                          alt={v.face_id}
                          className="w-10 h-10 rounded-lg object-cover border border-dark-500 shadow-sm"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-dark-700 flex items-center justify-center border border-dark-600">
                          <User className="w-5 h-5 text-slate-400" />
                        </div>
                      )}
                    </td>
                    <td className="py-4 px-6 font-mono font-bold text-white group-hover:text-brand-blue transition">
                      {v.face_id}
                    </td>
                    <td className="py-4 px-6">
                      <StatusBadge type="presence" value={v.status} />
                    </td>
                    <td className="py-4 px-6 text-xs text-slate-300">
                      {new Date(v.first_seen).toLocaleString()}
                    </td>
                    <td className="py-4 px-6 text-xs text-slate-300">
                      {new Date(v.last_seen).toLocaleString()}
                    </td>
                    <td className="py-4 px-6 text-center">
                      <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-dark-700 text-slate-200 border border-dark-600">
                        {v.visit_count}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-white inline transition-transform group-hover:translate-x-0.5" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Visitor Detail Modal */}
      <VisitorModal
        faceId={selectedFaceId}
        onClose={() => setSelectedFaceId(null)}
      />
    </div>
  );
}
