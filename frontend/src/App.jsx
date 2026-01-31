/**
 * Main App component with routing configuration.
 *
 * This is the nurse tablet web app for managing patient appointments.
 * Routes:
 * - / : Dashboard with calendar view
 * - /appointments/:id : Individual appointment details
 * - /flags : List of follow-up flags
 * - /login : Authentication (optional)
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import AppointmentDetail from './pages/AppointmentDetail'
import Flags from './pages/Flags'
import Login from './pages/Login'

function App() {
  // TODO: Implement actual auth check
  const isAuthenticated = true // Placeholder

  return (
    <BrowserRouter>
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<Login />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="appointments/:id" element={<AppointmentDetail />} />
          <Route path="flags" element={<Flags />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
