import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import LiveCamera from './pages/LiveCamera';
import Visitors from './pages/Visitors';
import Events from './pages/Events';
import Analytics from './pages/Analytics';
import RegisteredFaces from './pages/RegisteredFaces';
import System from './pages/System';
import VideoAnalysis from './pages/VideoAnalysis';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="live" element={<LiveCamera />} />
          <Route path="analyze" element={<VideoAnalysis />} />
          <Route path="visitors" element={<Visitors />} />
          <Route path="events" element={<Events />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="registrations" element={<RegisteredFaces />} />
          <Route path="system" element={<System />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

