import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import Shell, { PlantShell } from './components/Shell'
import Home from './pages/Home'
import NotFound from './pages/NotFound'
import Onboarding from './pages/Onboarding'
import PlantCare from './pages/PlantCare'
import PlantChat from './pages/PlantChat'
import PlantDetail from './pages/PlantDetail'
import PlantHistory from './pages/PlantHistory'

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          {/* Top-level shell with global header + nav */}
          <Route element={<Shell />}>
            <Route path="/" element={<Home />} />
            <Route path="/onboarding" element={<Onboarding />} />

            {/* Plant sub-shell with shared tab navigation */}
            <Route path="/plants/:plantId" element={<PlantShell />}>
              <Route index element={<PlantDetail />} />
              <Route path="care" element={<PlantCare />} />
              <Route path="chat" element={<PlantChat />} />
              <Route path="history" element={<PlantHistory />} />
            </Route>
          </Route>

          {/* Fallbacks */}
          <Route path="/index.html" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  )
}
