import { Link } from 'react-router-dom'
import Layout from '../components/Layout'
import { useAuth } from '../auth/AuthProvider'

export default function LandingPage() {
  const { isAuthenticated, user } = useAuth()

  return (
    <Layout>
      <div className="text-center">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          Welcome to Cube Foundry
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          The ultimate platform for managing and analyzing your Magic: The Gathering cubes
        </p>

        {isAuthenticated ? (
          <div className="space-x-4">
            <p className="text-gray-500 mb-4">Welcome back, <span className="font-semibold text-gray-800">{user?.username}</span>!</p>
            <Link
              to="/cubes"
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg text-lg font-medium hover:bg-blue-700"
            >
              My Cubes
            </Link>
            <Link
              to="/join-draft"
              className="inline-block bg-gray-200 text-gray-900 px-6 py-3 rounded-lg text-lg font-medium hover:bg-gray-300"
            >
              Join Draft
            </Link>
          </div>
        ) : (
          <div className="space-x-4">
            <Link
              to="/auth/register"
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg text-lg font-medium hover:bg-blue-700"
            >
              Get Started
            </Link>
            <Link
              to="/auth/login"
              className="inline-block bg-gray-200 text-gray-900 px-6 py-3 rounded-lg text-lg font-medium hover:bg-gray-300"
            >
              Sign In
            </Link>
          </div>
        )}

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-xl font-bold mb-2">Manage Your Cubes</h3>
            <p className="text-gray-600">
              Create and organize your Magic cube collection with ease
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-xl font-bold mb-2">Host Draft Events</h3>
            <p className="text-gray-600">
              Set up draft events and track player performance
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-xl font-bold mb-2">Analytics & Insights</h3>
            <p className="text-gray-600">
              Get detailed analytics on card performance and player stats
            </p>
          </div>
        </div>
      </div>
    </Layout>
  )
}
