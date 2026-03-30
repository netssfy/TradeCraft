import StrategyManager from './StrategyManager';

interface TraderStrategySectionProps {
  traderId: string;
  onUpdate: () => void;
}

export default function TraderStrategySection({ traderId, onUpdate }: TraderStrategySectionProps) {
  return <StrategyManager traderId={traderId} onUpdate={onUpdate} />;
}

