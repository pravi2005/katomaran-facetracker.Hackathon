import React, { useEffect, useState } from 'react';
import { UserCheck, Calendar, Clock, Eye, User } from 'lucide-react';
import { api } from '../api';
import VisitorModal from '../components/VisitorModal';

export default function RegisteredFaces() {
  const [faces, setFaces] = useState([]);
  const [selectedFaceId, setSelectedFaceId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getRegistrations()
      .then(setFaces)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Registered Face Gallery</h2>
        <p className="text-sm text-slate-400 mt-1">
          Stored identity embeddings and representative reference portraits
        </p>
      </div>

      {loading ? (
        <div className="py-20 text-center text-slate-400">Loading gallery...</div>
      ) : faces.length === 0 ? (
        <div className="py-20 text-center bg-dark-800 border border-dark-600 rounded-2xl p-8">
          <UserCheck className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No faces registered yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Faces that meet detection quality thresholds are automatically registered as F001, F002, etc.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {faces.map((face) => (
            <div
              key={face.face_id}
              onClick={() => setSelectedFaceId(face.face_id)}
              className="bg-dark-800 border border-dark-600 rounded-2xl overflow-hidden hover:border-brand-blue/50 transition-all duration-200 cursor-pointer group shadow-sm flex flex-col"
            >
              {/* Image Header */}
              <div className="relative aspect-square w-full bg-dark-900 overflow-hidden flex items-center justify-center">
                {face.representative_image_path ? (
                  <img
                    src={api.getImageUrl(face.representative_image_path)}
                    alt={face.face_id}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                ) : (
                  <User className="w-16 h-16 text-slate-600" />
                )}
                <div className="absolute top-3 right-3 bg-dark-900/80 backdrop-blur-sm border border-dark-600 px-2 py-0.5 rounded text-[11px] font-mono text-emerald-400 font-bold">
                  #{face.seq}
                </div>
              </div>

              {/* Body */}
              <div className="p-5 flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-lg font-bold text-white font-mono group-hover:text-brand-blue transition">
                      {face.face_id}
                    </h4>
                    <span className="text-xs font-mono text-slate-400 bg-dark-700 px-2 py-0.5 rounded">
                      {face.visit_count} visit{face.visit_count > 1 ? 's' : ''}
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-400">
                    <div className="flex items-center space-x-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      <span>{new Date(face.registered_at).toLocaleDateString()}</span>
                    </div>
                    {face.last_seen && (
                      <div className="flex items-center space-x-1.5">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        <span>Last: {new Date(face.last_seen).toLocaleTimeString()}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-dark-700 flex items-center justify-between text-xs text-brand-blue font-medium group-hover:translate-x-0.5 transition-transform">
                  <span>View Timeline</span>
                  <Eye className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Visitor Detail Modal */}
      <VisitorModal
        faceId={selectedFaceId}
        onClose={() => setSelectedFaceId(null)}
      />
    </div>
  );
}
