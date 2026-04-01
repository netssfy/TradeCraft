import StrategyManager from './StrategyManager';

interface TraderStrategySectionProps {
  traderId: string;
  onUpdate: () => void;
  onRunBacktest?: () => void;
  runningBacktest?: boolean;
}

export default function TraderStrategySection({
  traderId,
  onUpdate,
  onRunBacktest,
  runningBacktest,
}: TraderStrategySectionProps) {
  return (
    <StrategyManager
      traderId={traderId}
      onUpdate={onUpdate}
      onRunBacktest={onRunBacktest}
      runningBacktest={runningBacktest}
    />
  );
}
