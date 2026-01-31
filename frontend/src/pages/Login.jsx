/**
 * Login page for nurse authentication.
 *
 * Redesigned to match Figma design with:
 * - Gradient background
 * - Heart icon branding
 * - Clean form design
 * - Demo credentials display
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Heart, LogIn } from 'lucide-react'
import { login } from '../api/client'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    // Demo mode - allow demo credentials
    if (email === 'nurse@hospital.com' && password === 'nurse123') {
      localStorage.setItem('isAuthenticated', 'true')
      localStorage.setItem('auth_token', 'demo-token')
      localStorage.setItem('nurseName', 'Jessica Williams')
      // Use a consistent UUID for demo user
      localStorage.setItem('user_id', '12345678-1234-5678-1234-567812345678')
      navigate('/')
      return
    }

    // Try actual backend login
    try {
      const data = await login(email, password)
      localStorage.setItem('isAuthenticated', 'true')
      localStorage.setItem('nurseName', data.user?.first_name + ' ' + data.user?.last_name || 'Nurse')
      if (data.user?.id) {
        localStorage.setItem('user_id', data.user.id)
      }
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials. Try nurse@hospital.com / nurse123')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-full mb-4">
              <Heart size={32} className="text-white" fill="currentColor" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Rural Healthcare Portal</h1>
            <p className="text-gray-600">Referral Management System</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="nurse@hospital.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                'Signing in...'
              ) : (
                <>
                  <LogIn size={20} />
                  Sign In
                </>
              )}
            </button>
          </form>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-gray-700 font-medium mb-1">Demo Credentials:</p>
            <p className="text-sm text-gray-600">Email: nurse@hospital.com</p>
            <p className="text-sm text-gray-600">Password: nurse123</p>
          </div>
        </div>

        <p className="text-center text-gray-600 text-sm mt-6">
          Healthcare Management System © 2026
        </p>
      </div>
    </div>
  )
}
