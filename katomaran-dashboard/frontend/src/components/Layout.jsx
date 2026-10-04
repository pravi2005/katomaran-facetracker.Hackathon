import React, { useState, useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Video,
  Upload,
  Users,
  History,
  BarChart3,
  UserCheck,
  Server,
  Activity,
  Clock,
  Shield,
  Layers,
} from 'lucide-react';
import { api } from '../api';

export default function Layout() {
  const [time, setTime] = useState(new Date());
  const [systemOk, setSystemOk] = useState(true);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    api.getHealth()
      .then((res) => setSystemOk(res.status === 'healthy'))
      .catch(() => setSystemOk(false));
  }, []);

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/live', label: 'Live Camera', icon: Video },
    { to: '/analyze', label: 'Video Analysis', icon: Upload },
    { to: '/visitors', label: 'Visitors', icon: Users },
    { to: '/events', label: 'Events', icon: History },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/registrations', label: 'Registered Faces', icon: UserCheck },
    { to: '/system', label: 'System', icon: Server },
  ];

  return (
    <div className="flex h-screen bg-dark-900 text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-800 border-r border-dark-600 flex flex-col flex-shrink-0">
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-dark-600">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-blue to-brand-cyan flex items-center justify-center shadow-lg shadow-brand-blue/20">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-white block leading-tight">
                KATOMARAN
              </span>
              <span className="text-[10px] uppercase tracking-widest font-semibold text-brand-cyan">
                AI Vision
              </span>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-brand-blue/15 text-brand-blue border border-brand-blue/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-dark-700/50'
                  }`
                }
              >
                <Icon className="w-4 h-4 mr-3 flex-shrink-0" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Pipeline Tag */}
        <div className="p-4 border-t border-dark-600 bg-dark-800/50">
          <div className="p-3 rounded-xl bg-dark-700/60 border border-dark-600/80">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span className="font-semibold text-slate-300">Model Stack</span>
              <span className="text-[10px] text-brand-emerald bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">Active</span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono leading-relaxed">
              YOLOv8n + InsightFace<br/>
              ArcFace 512-d (CPU)
            </p>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="h-16 bg-dark-800 border-b border-dark-600 flex items-center justify-between px-8 flex-shrink-0">
          <div>
            <h1 className="text-base font-semibold text-white tracking-tight">
              Katomaran Face Intelligence
            </h1>
            <p className="text-xs text-slate-400">
              Autonomous Face Detection, Re-ID & Presence Tracker
            </p>
          </div>

          <div className="flex items-center space-x-6">
            {/* System Status Indicator */}
            <div className="flex items-center space-x-2 text-xs font-medium px-3 py-1.5 rounded-full bg-dark-700 border border-dark-600">
              <span className={`w-2 h-2 rounded-full ${systemOk ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`}></span>
              <span className={systemOk ? 'text-emerald-400' : 'text-rose-400'}>
                {systemOk ? 'System Online' : 'System Offline'}
              </span>
            </div>

            {/* Current Time Clock */}
            <div className="flex items-center space-x-2 text-xs font-mono text-slate-300 bg-dark-700/50 px-3 py-1.5 rounded-lg border border-dark-600/80">
              <Clock className="w-3.5 h-3.5 text-brand-cyan" />
              <span>{time.toLocaleTimeString()}</span>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-8 bg-dark-900">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
