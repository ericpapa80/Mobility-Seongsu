import { useNavigate } from 'react-router-dom';
import './Header.css';

export type ViewTab = 'infrastructure' | 'flow' | 'risk';

interface Props {
  activeView: ViewTab;
  onViewChange: (v: ViewTab) => void;
  onDownload: () => void;
  onAdmin: () => void;
}

const VIEW_TABS: { key: ViewTab; label: string }[] = [
  { key: 'infrastructure', label: 'Infrastructure' },
  { key: 'flow', label: 'Dynamic Flow' },
  { key: 'risk', label: 'Risk & Safety' },
];

export default function Header({ activeView, onViewChange, onDownload, onAdmin }: Props) {
  const navigate = useNavigate();

  return (
    <header className="header">
      <div className="header-left">
        <div className="logo" onClick={() => navigate('/')}>
          <div className="logo-icon"><i className="ri-route-line" /></div>
          <span className="logo-text">성수 클러스터 모빌리티 현황</span>
          <span className="logo-badge">Phase 1</span>
        </div>
      </div>

      <nav className="header-center">
        {VIEW_TABS.map((t) => (
          <button
            key={t.key}
            className={`header-tab${activeView === t.key ? ' active' : ''}`}
            onClick={() => onViewChange(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="header-right">
        <select className="period-select" defaultValue="2026-01">
          <option value="2026-01">2026년 1월</option>
          <option value="2025-Q4">2025년 4분기</option>
          <option value="2025-Q3">2025년 3분기</option>
        </select>
        <button className="header-btn" onClick={onDownload}>
          <i className="ri-download-2-line" /> 내보내기
        </button>
        <button className="header-btn admin" onClick={onAdmin}>
          <i className="ri-settings-3-line" /> 관리자
        </button>
      </div>
    </header>
  );
}
