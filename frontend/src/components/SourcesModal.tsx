import { useEffect, useState } from 'react';
import { api } from '../api/client';
import './Modal.css';

interface Source {
  id: string;
  name: string;
  provider: string;
  free?: string;
  schedule: string;
  unit?: string;
  api: string;
  usage?: string;
  target?: string;
  storage: string;
  status: string;
}

interface Cluster {
  id: string;
  label: string;
  items: Source[];
}

interface Props {
  open: boolean;
  onClose: () => void;
}

function formatNameWithBreak(name: string) {
  const idx = name.indexOf(' (');
  if (idx >= 0) {
    return (
      <>
        {name.slice(0, idx)}
        <br />
        {name.slice(idx + 1)}
      </>
    );
  }
  return name;
}

function SourceRow({ s }: { s: Source }) {
  return (
    <tr>
      <td className="sources-name">{formatNameWithBreak(s.name)}</td>
      <td>{s.provider}</td>
      <td>{s.free ?? '-'}</td>
      <td>{s.schedule}</td>
      <td className="sources-unit">{s.unit ?? '-'}</td>
      <td><code>{s.api}</code></td>
      <td className="sources-usage">{s.usage ?? '-'}</td>
      <td>{s.target ?? '-'}</td>
      <td>{s.storage}</td>
      <td>
        <span className={`sources-status ${s.status}`}>
          {s.status === 'active' ? '활성' : s.status === 'planned' ? '검토 중' : s.status}
        </span>
      </td>
    </tr>
  );
}

export default function SourcesModal({ open, onClose }: Props) {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    api
      .sources()
      .then((res) => {
        if (res.clusters?.length) {
          setClusters(res.clusters);
        } else if (res.sources?.length) {
          setClusters([{ id: 'all', label: '전체', items: res.sources as Source[] }]);
        } else {
          setClusters([]);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [open]);

  if (!open) return null;

  return (
    <div className="modal-backdrop sources-fullscreen" onClick={onClose}>
      <div className="modal-dialog wide sources fullscreen" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            <i className="ri-database-2-line" /> 데이터 출처
          </h3>
          <button className="modal-close" onClick={onClose}>
            <i className="ri-close-line" />
          </button>
        </div>
        <div className="modal-body">
          {loading && (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
              로딩 중...
            </div>
          )}
          {error && (
            <div style={{ padding: '12px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px', color: 'var(--accent-red)', marginBottom: '12px' }}>
              {error}
            </div>
          )}
          {!loading && !error && clusters.length > 0 && (
            <div className="sources-table-wrap">
              {clusters.map((cluster) => (
                <div key={cluster.id} className="sources-cluster">
                  <h4 className="sources-cluster-title">{cluster.label}</h4>
                  <table className="sources-table">
                    <colgroup>
                      <col className="col-name" />
                      <col className="col-provider" />
                      <col className="col-free" />
                      <col className="col-schedule" />
                      <col className="col-unit" />
                      <col className="col-api" />
                      <col className="col-usage" />
                      <col className="col-target" />
                      <col className="col-storage" />
                      <col className="col-status" />
                    </colgroup>
                    <thead>
                      <tr>
                        <th>출처명</th>
                        <th>제공처</th>
                        <th>유무료</th>
                        <th>갱신</th>
                        <th>단위</th>
                        <th>제공방식</th>
                        <th>활용</th>
                        <th>대상</th>
                        <th>저장소</th>
                        <th>상태</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cluster.items.map((s) => (
                        <SourceRow key={s.id} s={s as Source} />
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="modal-btn secondary" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
