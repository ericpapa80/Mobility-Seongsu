import { useState, useRef, useCallback, useEffect } from 'react';
import type { TrafficMode } from './Sidebar';
import './TimeSlider.css';

interface Props {
  hour: number;
  onChange: (hour: number | ((prev: number) => number)) => void;
  trafficMode?: TrafficMode;
  trafficLayerOn?: boolean;
}

const LABELS = ['0시', '3시', '6시', '9시', '12시', '15시', '18시', '21시', '23시'];

export default function TimeSlider({ hour, onChange, trafficMode = 'pattern', trafficLayerOn = false }: Props) {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isPeak = (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19);
  const isTrafficRealtime = trafficLayerOn && trafficMode === 'realtime';
  const nowHour = new Date().getHours();

  useEffect(() => {
    if (isTrafficRealtime) {
      onChange(nowHour);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTrafficRealtime]);

  const togglePlay = useCallback(() => setPlaying(p => !p), []);
  const cycleSpeed = useCallback(() => setSpeed(s => (s >= 4 ? 1 : s * 2)), []);

  useEffect(() => {
    if (playing) {
      intervalRef.current = setInterval(() => {
        onChange(prev => (prev + 1) % 24);
      }, 1000 / speed);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [playing, speed, onChange]);

  const nowPercent = (nowHour / 23) * 100;

  return (
    <div className="time-slider-panel">
      <div className="time-slider-header">
        <div className="time-slider-title">
          <i className="ri-time-line" />
          시간대 선택
          <span className="time-current">
            {String(hour).padStart(2, '0')}:00
            {isPeak && <span className="peak-badge">피크</span>}
          </span>
          {isTrafficRealtime && (
            <span className="realtime-badge">
              <i className="ri-live-line" /> 교통: 실시간
            </span>
          )}
        </div>
        <div className="time-slider-controls">
          <button className="ts-btn" onClick={togglePlay} title={playing ? '정지' : '재생'}>
            <i className={playing ? 'ri-pause-fill' : 'ri-play-fill'} />
          </button>
          <button className="ts-btn speed-btn" onClick={cycleSpeed} title="배속">
            x{speed}
          </button>
        </div>
      </div>
      <div className="time-range-wrap">
        <input
          type="range"
          min={0}
          max={23}
          value={hour}
          onChange={(e) => onChange(Number(e.target.value))}
          className="time-range"
        />
        {isTrafficRealtime && (
          <div className="now-marker" style={{ left: `${nowPercent}%` }} title={`현재 ${nowHour}시`} />
        )}
      </div>
      <div className="time-labels">
        {LABELS.map((l) => (
          <span key={l} className="time-label">{l}</span>
        ))}
      </div>
    </div>
  );
}
