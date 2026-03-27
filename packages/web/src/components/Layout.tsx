import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { theme, toggle } = useTheme();

  return (
    <div style={{ minHeight: '100vh' }}>
      <header
        style={{
          background: 'var(--header-bg)',
          borderBottom: '1px solid var(--header-border)',
          padding: '12px 0',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          transition: 'background var(--transition), border-color var(--transition)',
          ...(theme === 'light' ? {
            backdropFilter: 'blur(16px) saturate(180%)',
            WebkitBackdropFilter: 'blur(16px) saturate(180%)',
          } : {}),
        }}
      >
        <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <Link to="/" style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>
              TradeCraft
            </Link>
            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              韭菜的交易世界
            </span>
          </div>
          <button
            className="theme-toggle"
            onClick={toggle}
            title={theme === 'dark' ? '切换到明亮模式' : '切换到暗色模式'}
            aria-label={theme === 'dark' ? '切换到明亮模式' : '切换到暗色模式'}
          >
            <span className="theme-icon theme-icon--dark">🌙</span>
            <span className="theme-icon theme-icon--light">☀️</span>
          </button>
        </div>
      </header>
      <main className="container" style={{ paddingTop: 24, paddingBottom: 48 }}>
        {children}
      </main>
    </div>
  );
}
