/**
 * Main layout component with vertical navigation.
 *
 * Features:
 * - Vertical sidebar navigation (Figma design)
 * - Nurse profile and logout
 * - Flag banner for urgent items
 * - Content area with outlet
 */

import { useState, useEffect } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getOpenFlags } from '../api/client'
import VerticalNav from './VerticalNav'
import FlagBanner from './FlagBanner'

export default function Layout() {
  const navigate = useNavigate()
  const [nurseName, setNurseName] = useState('Jessica Williams')

  useEffect(() => {
    // Check authentication
    const isAuth = localStorage.getItem('isAuthenticated') || localStorage.getItem('auth_token')
    if (!isAuth) {
      navigate('/login')
    }

    // Get nurse name from localStorage
    const storedName = localStorage.getItem('nurseName')
    if (storedName) {
      setNurseName(storedName)
    }
  }, [navigate])

  // Fetch open flags for banner
  const { data: flags = [] } = useQuery({
    queryKey: ['flags', 'open'],
    queryFn: getOpenFlags,
    refetchInterval: 30000,
  })

  const urgentFlags = flags.filter(
    (f) => f.priority === 'urgent' || f.priority === 'high',
  )

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to log out?')) {
      localStorage.removeItem('isAuthenticated')
      localStorage.removeItem('auth_token')
      localStorage.removeItem('nurseName')
      navigate('/login')
    }
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <VerticalNav nurseName={nurseName} onLogout={handleLogout} />
      
      <main className="flex-1 ml-64">
        {/* Urgent flags banner */}
        {urgentFlags.length > 0 && <FlagBanner flags={urgentFlags} />}
        
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
