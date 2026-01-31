/**
 * Main App component with routing configuration.
 *
 * This is the nurse tablet web app for managing patient referrals.
 * Routes:
 * - / : Dashboard with calendar view
 * - /referrals/:id : Individual referral details
 * - /flags : List of follow-up flags
 * - /login : Authentication (optional)
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ReferralDetail from './pages/ReferralDetail'
import Flags from './pages/Flags'
import Login from './pages/Login'

function App() {
  // Check for auth token in localStorage
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => !!localStorage.getItem('auth_token')
  )

  // Listen for storage changes (e.g., login/logout in another tab)
  useEffect(() => {
    const handleStorageChange = () => {
      setIsAuthenticated(!!localStorage.getItem('auth_token'))
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

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
          <Route index element={<Dashboard />} />
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
