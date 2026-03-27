import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { Portfolio } from '@tradecraft/shared/types';

interface PortfolioChartProps {
  portfolio: Portfolio;
  initialCash: number;
}

interface ChartDataPoint {
  date: string;
  returnPct: number;
  netValue: number;
}

export default function PortfolioChart({ portfolio, initialCash }: PortfolioChartProps) {
  const data = useMemo<ChartDataPoint[]>(() => {
    return portfolio.snapshots.map((snap) => {
      const totalValue =
        snap.cash +
        Object.values(snap.positions).reduce((sum, p) => sum + p.quantity * p.avg_cost, 0);
      const returnPct = ((totalValue - initialCash) / initialCash) * 100;
      return { date: snap.date, returnPct, netValue: totalValue };
    });
  }, [portfolio, initialCash]);

  if (data.length < 2) {
    return (
      <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
        数据不足，无法绘制曲线
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
          <XAxis
            dataKey="date"
            stroke="var(--text-muted)"
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            tickLine={false}
          />
          <YAxis
            stroke="var(--text-muted)"
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            tickLine={false}
            tickFormatter={(v: number) => `${v.toFixed(1)}%`}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value: number, name: string) => {
              if (name === 'returnPct') return [`${value.toFixed(2)}%`, '累计收益率'];
              return [value, name];
            }}
            labelFormatter={(label: string) => `日期: ${label}`}
          />
          <Line
            type="monotone"
            dataKey="returnPct"
            stroke="var(--accent)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
