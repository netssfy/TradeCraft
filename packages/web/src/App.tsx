import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import TraderListPage from './pages/TraderListPage';
import CreateTraderPage from './pages/CreateTraderPage';
import TraderDetailPage from './pages/TraderDetailPage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<TraderListPage />} />
        <Route path="/traders/create" element={<CreateTraderPage />} />
        <Route path="/traders/:id" element={<TraderDetailPage />} />
      </Routes>
    </Layout>
  );
}
