import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { theme, toggle } = useTheme();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <Link to="/" className="brand-mark" style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)' }}>
              TradeCraft
            </Link>
            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              智能交易工作台
            </span>
          </div>
          <button
            className="theme-toggle"
            onClick={toggle}
            title={theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
            aria-label={theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
          >
            <span className="theme-icon theme-icon--dark">🌙</span>
            <span className="theme-icon theme-icon--light">☀</span>
          </button>
        </div>
      </header>
      <main className="container" style={{ paddingTop: 24, paddingBottom: 48 }}>
        {children}
      </main>
    </div>
  );
}
