import { Link } from 'react-router-dom';
import { useI18n } from '../hooks/useI18n';
import { useTheme } from '../hooks/useTheme';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { theme, toggle } = useTheme();
  const { lang, setLang, tx } = useI18n();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <Link to="/" className="brand-mark" style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)' }}>
              TradeCraft
            </Link>
            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{tx('智能交易工作台', 'Intelligent Trading Workspace')}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="lang-toggle" role="group" aria-label={tx('语言切换', 'Language toggle')}>
              <button
                className={`lang-toggle__btn ${lang === 'zh' ? 'lang-toggle__btn--active' : ''}`}
                onClick={() => setLang('zh')}
                aria-label="Switch to Chinese"
                title="中文"
              >
                中文
              </button>
              <button
                className={`lang-toggle__btn ${lang === 'en' ? 'lang-toggle__btn--active' : ''}`}
                onClick={() => setLang('en')}
                aria-label="Switch to English"
                title="English"
              >
                EN
              </button>
            </div>

            <button
              className="theme-toggle"
              onClick={toggle}
              title={theme === 'dark' ? tx('切换到亮色模式', 'Switch to light mode') : tx('切换到暗色模式', 'Switch to dark mode')}
              aria-label={theme === 'dark' ? tx('切换到亮色模式', 'Switch to light mode') : tx('切换到暗色模式', 'Switch to dark mode')}
            >
              <span className="theme-icon theme-icon--dark">D</span>
              <span className="theme-icon theme-icon--light">L</span>
            </button>
          </div>
        </div>
      </header>
      <main className="container" style={{ paddingTop: 24, paddingBottom: 48 }}>
        {children}
      </main>
    </div>
  );
}
