import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { CpseProvider } from './context/CpseContext';
import { DashboardPage } from './pages/DashboardPage';
import { CpsesPage } from './pages/CpsesPage';
import { MaterialsPage } from './pages/MaterialsPage';
import { MatchingPage } from './pages/MatchingPage';
import { ReviewPage } from './pages/ReviewPage';
import { NationalMaterialsPage } from './pages/NationalMaterialsPage';
import { AuditPage } from './pages/AuditPage';

export const App: React.FC = () => {
  return (
    <CpseProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/cpses" element={<CpsesPage />} />
            <Route path="/materials" element={<MaterialsPage />} />
            <Route path="/matching" element={<MatchingPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/national-materials" element={<NationalMaterialsPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CpseProvider>
  );
};

export default App;

