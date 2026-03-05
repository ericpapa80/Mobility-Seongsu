/**
 * 만원 단위 값을 억/만 단위로 변환하여 표시
 * (peco_total, times, weekday 등 모든 매출 필드는 만원 단위)
 */
export function fmtWon(v: number): string {
  if (v >= 10000) return Math.round(v / 10000).toLocaleString() + '억';
  return v.toLocaleString() + '만';
}

/** d3 축 tick 포맷용 (만원 → 억/만) */
export function fmtAxisWon(v: { valueOf(): number }): string {
  const n = +v;
  if (n === 0) return '0';
  if (n >= 10000) {
    const b = n / 10000;
    return (Number.isInteger(b) ? b : b.toFixed(1)) + '억';
  }
  return n.toLocaleString() + '만';
}
