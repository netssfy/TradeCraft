import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import TraderListPage from './pages/TraderListPage';
import CreateTraderPage from './pages/CreateTraderPage';
import TraderDetailPage from './pages/TraderDetailPage';
import StrategyCodePage from './pages/StrategyCodePage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<TraderListPage />} />
        <Route path="/traders/create" element={<CreateTraderPage />} />
        <Route path="/traders/:id" element={<TraderDetailPage />} />
        <Route path="/traders/:id/strategy/:filename" element={<StrategyCodePage />} />
      </Routes>
    </Layout>
  );
}
