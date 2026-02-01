import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import CalendarPage from './pages/CalendarPage'
import DashboardNew from './pages/DashboardNew'
import ReferralDetail from './pages/ReferralDetail'
import Flags from './pages/Flags'
import Login from './pages/Login'

function App() {
  // Check if user is authenticated
  const isAuthenticated = () => {
    return localStorage.getItem('isAuthenticated') === 'true' || 
           localStorage.getItem('auth_token') !== null
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<Login />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            isAuthenticated() ? <Layout /> : <Navigate to="/login" replace />
          }
        >
          <Route index element={<Navigate to="/calendar" replace />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="dashboard" element={<DashboardNew />} />
          <Route path="referrals/:id" element={<ReferralDetail />} />
          <Route path="flags" element={<Flags />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/calendar" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App