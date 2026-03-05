import './Modal.css';

interface Props { open: boolean; onClose: () => void; }

const ADMIN_SECTIONS = [
  {
    title: 'API 데이터 갱신',
    icon: 'ri-refresh-line',
    items: ['서울 열린데이터 수동 갱신', 'SK Open API 재동기화', 'SGIS 통계 수집'],
  },
  {
    title: '이상치 탐지',
    icon: 'ri-alert-line',
    items: ['V/C 비율 임계치 설정', '승하차 이상치 기준 조정', '자동 알림 ON/OFF'],
  },
  {
    title: '데이터 백업',
    icon: 'ri-database-2-line',
    items: ['전체 DB 백업', '증분 백업 스케줄', '복원 포인트 관리'],
  },
  {
    title: '가중치 설정',
    icon: 'ri-equalizer-line',
    items: ['안전지수 가중치', '혼잡도 계산 파라미터', '위험도 점수 조정'],
  },
];

export default function AdminModal({ open, onClose }: Props) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3><i className="ri-settings-3-line" /> 관리자 설정</h3>
          <button className="modal-close" onClick={onClose}><i className="ri-close-line" /></button>
        </div>
        <div className="modal-body">
          <div className="admin-grid">
            {ADMIN_SECTIONS.map((s) => (
              <div key={s.title} className="admin-card">
                <div className="admin-card-header">
                  <i className={s.icon} />
                  <span>{s.title}</span>
                </div>
                <ul className="admin-items">
                  {s.items.map((item) => (
                    <li key={item}>
                      <span>{item}</span>
                      <button className="admin-action-btn">실행</button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <div className="modal-footer">
          <button className="modal-btn secondary" onClick={onClose}>닫기</button>
        </div>
      </div>
    </div>
  );
}
