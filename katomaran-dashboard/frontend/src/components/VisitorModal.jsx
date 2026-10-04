import React, { useEffect, useState } from 'react';
import { X, Calendar, User, Clock, ShieldCheck, ArrowRight } from 'lucide-react';
import { api } from '../api';
import StatusBadge from './StatusBadge';

export default function VisitorModal({ faceId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!faceId) return;
    setLoading(true);
    api.getVisitorDetail(faceId)
      .then(setData)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [faceId]);

  if (!faceId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-dark-800 border border-dark-600 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-dark-600">
          <div className="flex items-center space-x-4">
            {data?.representative_image_path ? (
              <img
                src={api.getImageUrl(data.representative_image_path)}
                alt={faceId}
                className="w-14 h-14 rounded-xl object-cover border border-dark-500 shadow-md"
              />
            ) : (
              <div className="w-14 h-14 rounded-xl bg-dark-700 flex items-center justify-center border border-dark-600">
                <User className="w-7 h-7 text-slate-400" />
              </div>
            )}
            <div>
              <div className="flex items-center space-x-3">
                <h3 className="text-xl font-bold text-white font-mono">{faceId}</h3>
                {data && <StatusBadge type="presence" value={data.status} />}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Registered: {data?.registered_at ? new Date(data.registered_at).toLocaleString() : 'Loading...'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-dark-700 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {loading ? (
            <div className="py-12 text-center text-slate-400">Loading visitor data...</div>
          ) : !data ? (
            <div className="py-12 text-center text-slate-400">Visitor details not found.</div>
          ) : (
            <>
              {/* Event Timeline */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4 flex items-center">
                  <Clock className="w-4 h-4 mr-2 text-brand-blue" />
                  Presence Event History ({data.events?.length || 0})
                </h4>

                <div className="space-y-3">
                  {data.events?.map((ev) => (
                    <div
                      key={ev.event_id}
                      className="flex items-center justify-between p-3.5 rounded-xl bg-dark-700/40 border border-dark-600 hover:border-dark-500 transition"
                    >
                      <div className="flex items-center space-x-3">
                        <StatusBadge type="event" value={ev.event_type} />
                        <div>
                          <p className="text-xs font-medium text-slate-200">
                            {new Date(ev.timestamp).toLocaleString()}
                          </p>
                          <p className="text-[11px] text-slate-400 font-mono">
                            Video Time: {ev.source_timestamp} | Track ID: #{ev.track_id}
                            {ev.reason && ` | Reason: ${ev.reason}`}
                          </p>
                        </div>
                      </div>

                      {ev.image_path && (
                        <img
                          src={api.getImageUrl(ev.image_path)}
                          alt={`${ev.face_id} ${ev.event_type}`}
                          className="w-10 h-10 rounded-lg object-cover border border-dark-500"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
