import './Modal.css';

interface Props { open: boolean; onClose: () => void; }

const FORMATS = [
  { id: 'csv', label: 'CSV', icon: 'ri-file-text-line', desc: '원시 데이터 테이블 (.csv)' },
  { id: 'excel', label: 'Excel', icon: 'ri-file-excel-2-line', desc: '분석 스프레드시트 (.xlsx)' },
  { id: 'pdf', label: 'PDF', icon: 'ri-file-pdf-2-line', desc: '보고서 형식 (.pdf)' },
];

export default function DownloadModal({ open, onClose }: Props) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3><i className="ri-download-2-line" /> 데이터 내보내기</h3>
          <button className="modal-close" onClick={onClose}><i className="ri-close-line" /></button>
        </div>
        <div className="modal-body">
          <label className="modal-label">내보내기 범위</label>
          <select className="modal-select">
            <option>현재 시간대 (선택된 시간)</option>
            <option>전체 시간대 (0~23시)</option>
            <option>피크 시간대만</option>
          </select>

          <label className="modal-label">포맷 선택</label>
          <div className="format-grid">
            {FORMATS.map((f) => (
              <label key={f.id} className="format-option">
                <input type="radio" name="format" defaultChecked={f.id === 'csv'} />
                <div className="format-card">
                  <i className={f.icon} />
                  <span className="format-name">{f.label}</span>
                  <span className="format-desc">{f.desc}</span>
                </div>
              </label>
            ))}
          </div>
        </div>
        <div className="modal-footer">
          <button className="modal-btn secondary" onClick={onClose}>취소</button>
          <button className="modal-btn primary"><i className="ri-download-2-line" /> 다운로드</button>
        </div>
      </div>
    </div>
  );
}
