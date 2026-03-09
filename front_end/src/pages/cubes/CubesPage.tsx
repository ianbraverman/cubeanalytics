import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../auth/AuthProvider'
import { cubesApi } from '../../api/cubes'
import Layout from '../../components/Layout'

export default function CubesPage() {
  const { user } = useAuth()

  const { data: cubes, isLoading } = useQuery({
    queryKey: ['userCubes', user?.id],
    queryFn: () => cubesApi.getUserCubes(user!.id),
    enabled: !!user,
  })

  return (
    <Layout>
      <div>
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">My Cubes</h1>
          <Link
            to="/cubes/new"
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            Create New Cube
          </Link>
        </div>

        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading cubes...</p>
          </div>
        ) : cubes && cubes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cubes.map((cube) => (
              <Link
                key={cube.id}
                to={`/cubes/${cube.id}`}
                className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow"
              >
                <h2 className="text-xl font-semibold text-gray-900 mb-2">{cube.name}</h2>
                <p className="text-gray-600 mb-4">{cube.description || 'No description'}</p>
                <div className="text-sm text-gray-500">
                  <p>Created: {new Date(cube.created_at).toLocaleDateString()}</p>
                  <p>Updated: {new Date(cube.updated_at).toLocaleDateString()}</p>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">No cubes yet</h2>
            <p className="text-gray-600 mb-6">
              Create your first cube to start managing your Magic collection
            </p>
            <Link
              to="/cubes/new"
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700"
            >
              Create Your First Cube
            </Link>
          </div>
        )}
      </div>
    </Layout>
  )
}
