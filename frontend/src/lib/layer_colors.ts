import type { Color } from '@deck.gl/core';

export function speedColor(speed: number): Color {
  if (speed >= 40) return [16, 185, 129, 200];
  if (speed >= 25) return [245, 158, 11, 200];
  if (speed >= 15) return [239, 68, 68, 200];
  return [153, 27, 27, 220];
}

export function gradeColor(grade: number): Color {
  if (grade >= 5) return [255, 0, 0, 220];
  if (grade >= 4) return [255, 127, 0, 200];
  if (grade >= 3) return [255, 255, 0, 180];
  if (grade >= 2) return [49, 163, 84, 160];
  return [0, 104, 55, 140];
}

const STORE_CATEGORY_COLORS: Record<string, Color> = {
  '음식': [251, 146, 60, 200],
  '소매': [59, 130, 246, 200],
  '서비스': [244, 114, 182, 200],
};

export function storeCategoryColor(cat: string): Color {
  return STORE_CATEGORY_COLORS[cat] ?? [148, 163, 184, 160];
}

export function buildingColor(floors: number): Color {
  if (floors >= 10) return [139, 92, 246, 140];
  if (floors >= 4) return [59, 130, 246, 120];
  return [148, 163, 184, 100];
}

const INDUSTRY_COLORS: Color[] = [
  [139, 92, 246, 200],
  [59, 130, 246, 200],
  [16, 185, 129, 200],
  [251, 146, 60, 200],
  [236, 72, 153, 200],
  [245, 158, 11, 200],
  [6, 182, 212, 200],
  [244, 63, 94, 200],
];

const industryIndexMap = new Map<string, number>();

export function industryColor(industry: string): Color {
  if (!industryIndexMap.has(industry)) {
    industryIndexMap.set(industry, industryIndexMap.size);
  }
  return INDUSTRY_COLORS[industryIndexMap.get(industry)! % INDUSTRY_COLORS.length];
}

export const HOUR_TO_STORE_SLOT: Record<number, string> = {
  0: '심야', 1: '심야', 2: '심야',
  3: '새벽', 4: '새벽', 5: '새벽',
  6: '아침', 7: '아침', 8: '아침',
  9: '점심', 10: '점심', 11: '점심', 12: '점심', 13: '점심',
  14: '오후', 15: '오후', 16: '오후',
  17: '저녁', 18: '저녁', 19: '저녁', 20: '저녁',
  21: '밤', 22: '밤', 23: '밤',
};

export const HOUR_TO_TMZON: Record<number, string> = {
  0: '00~05', 1: '00~05', 2: '00~05', 3: '00~05', 4: '00~05', 5: '00~05',
  6: '06~10', 7: '06~10', 8: '06~10', 9: '06~10', 10: '06~10',
  11: '11~13', 12: '11~13', 13: '11~13',
  14: '14~16', 15: '14~16', 16: '14~16',
  17: '17~20', 18: '17~20', 19: '17~20', 20: '17~20',
  21: '21~23', 22: '21~23', 23: '21~23',
};

export const HEATMAP_COLOR_RANGE: [number, number, number, number][] = [
  [0, 25, 0, 25],
  [0, 104, 55, 100],
  [49, 163, 84, 160],
  [255, 255, 0, 200],
  [255, 127, 0, 230],
  [255, 0, 0, 255],
];

export const STORE_HEATMAP_RANGE: [number, number, number, number][] = [
  [255, 247, 236, 25],
  [253, 208, 162, 100],
  [253, 174, 107, 160],
  [241, 105, 19, 200],
  [217, 72, 1, 230],
  [140, 45, 4, 255],
];
