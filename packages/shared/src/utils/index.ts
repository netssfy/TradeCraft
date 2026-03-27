export const TRAIT_LABELS: Record<string, string> = {
  risk_appetite: '风险偏好',
  holding_horizon: '持仓周期',
  signal_preference: '信号偏好',
  position_construction: '仓位构建',
  exit_discipline: '退出纪律',
  universe_focus: '标的范围',
};

export function formatCurrency(value: number): string {
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatDate(dateStr: string): string {
  return dateStr;
}
