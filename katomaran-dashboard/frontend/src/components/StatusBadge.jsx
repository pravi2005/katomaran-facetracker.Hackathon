import React from 'react';

export default function StatusBadge({ type, value }) {
  if (type === 'presence') {
    const isPresent = value === 'Present';
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        isPresent ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-700/30 text-slate-400 border border-slate-700'
      }`}>
        <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${isPresent ? 'bg-emerald-400 animate-pulse' : 'bg-slate-400'}`}></span>
        {value}
      </span>
    );
  }

  if (type === 'event') {
    const isEntry = value === 'ENTRY';
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold tracking-wider ${
        isEntry ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
      }`}>
        {value}
      </span>
    );
  }

  if (type === 'system') {
    const isOk = value === 'READY' || value === 'CONNECTED' || value === 'ONLINE';
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        isOk ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
      }`}>
        <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${isOk ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
        {value}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300">
      {value}
    </span>
  );
}
