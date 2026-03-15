import { useState, useCallback } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import type { ViewTab } from './components/Header';
import Dashboard from './views/Dashboard';
import Strategy from './views/Strategy';

const STORAGE_KEY_VIEW = 'ms_activeView';
const VALID_VIEWS: ViewTab[] = ['infrastructure', 'flow', 'risk'];

function loadView(): ViewTab {
  const saved = localStorage.getItem(STORAGE_KEY_VIEW) as ViewTab | null;
  return saved && VALID_VIEWS.includes(saved) ? saved : 'flow';
}

export default function App() {
  const location = useLocation();
  const [activeView, setActiveView] = useState<ViewTab>(loadView);
  const [showDownload, setShowDownload] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const handleViewChange = useCallback((v: ViewTab) => {
    setActiveView(v);
    localStorage.setItem(STORAGE_KEY_VIEW, v);
  }, []);

  const isDashboard = location.pathname === '/';

  return (
    <>
      {isDashboard ? (
        <Header
          activeView={activeView}
          onViewChange={handleViewChange}
          onDownload={() => setShowDownload(true)}
          onAdmin={() => setShowAdmin(true)}
          onSources={() => setShowSources(true)}
        />
      ) : (
        <Header
          activeView={activeView}
          onViewChange={handleViewChange}
          onDownload={() => {}}
          onAdmin={() => {}}
          onSources={() => {}}
        />
      )}
      <Routes>
        <Route
          path="/"
          element={
            <Dashboard
              activeView={activeView}
              showDownload={showDownload}
              showAdmin={showAdmin}
              showSources={showSources}
              onCloseDownload={() => setShowDownload(false)}
              onCloseAdmin={() => setShowAdmin(false)}
              onCloseSources={() => setShowSources(false)}
            />
          }
        />
        <Route path="/strategy" element={<Strategy />} />
      </Routes>
    </>
  );
}
