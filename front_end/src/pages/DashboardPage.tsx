import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthProvider'
import { cubesApi } from '../api/cubes'
import Layout from '../components/Layout'

export default function DashboardPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [isDeleteMode, setIsDeleteMode] = useState(false)

  const { data: cubes, isLoading } = useQuery({
    queryKey: ['userCubes', user?.id],
    queryFn: () => cubesApi.getUserCubes(user!.id),
    enabled: !!user,
  })

  const deleteCubeMutation = useMutation({
    mutationFn: (cubeId: number) => cubesApi.deleteCube(cubeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userCubes', user?.id] })
    },
  })

  const handleDeleteCube = (cubeId: number, cubeName: string) => {
    if (window.confirm(`Are you sure you want to delete "${cubeName}"?`)) {
      deleteCubeMutation.mutate(cubeId)
    }
  }

  return (
    <Layout>
      <div>
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <div className="flex space-x-2">
            {cubes && cubes.length > 0 && (
              <button
                onClick={() => setIsDeleteMode(!isDeleteMode)}
                className={`px-4 py-2 rounded-md ${
                  isDeleteMode
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
                }`}
              >
                {isDeleteMode ? 'Cancel Delete' : 'Delete Cubes'}
              </button>
            )}
            <Link
              to="/cubes/new"
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              Create New Cube
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold text-gray-700">My Cubes</h3>
            <p className="text-3xl font-bold text-blue-600">{cubes?.length || 0}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold text-gray-700">Draft Events</h3>
            <p className="text-3xl font-bold text-green-600">0</p>
          </div>
          <Link to="/my-drafts" className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow block">
            <h3 className="text-lg font-semibold text-gray-700">My Drafts</h3>
            <p className="text-sm text-indigo-600 mt-1">View history &amp; rejoin active drafts →</p>
          </Link>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold mb-4">My Cubes</h2>
          {isLoading ? (
            <p className="text-gray-600">Loading...</p>
          ) : cubes && cubes.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {cubes.map((cube) => (
                <div
                  key={cube.id}
                  className={`border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-shadow relative ${
                    isDeleteMode ? 'bg-red-50' : ''
                  }`}
                >
                  {isDeleteMode ? (
                    <div className="flex flex-col h-full">
                      <h3 className="text-lg font-semibold text-gray-900">{cube.name}</h3>
                      <p className="text-gray-600 text-sm mt-1 flex-1">
                        {cube.description || 'No description'}
                      </p>
                      <p className="text-gray-500 text-xs mt-2 mb-4">
                        Created: {new Date(cube.created_at).toLocaleDateString()}
                      </p>
                      <button
                        onClick={(e) => {
                          e.preventDefault()
                          handleDeleteCube(cube.id, cube.name)
                        }}
                        className="w-full bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 font-semibold"
                        disabled={deleteCubeMutation.isPending}
                      >
                        ✕ Delete
                      </button>
                    </div>
                  ) : (
                    <Link
                      to={`/cubes/${cube.id}`}
                      className="block"
                    >
                      <h3 className="text-lg font-semibold text-gray-900">{cube.name}</h3>
                      <p className="text-gray-600 text-sm mt-1">
                        {cube.description || 'No description'}
                      </p>
                      <p className="text-gray-500 text-xs mt-2">
                        Created: {new Date(cube.created_at).toLocaleDateString()}
                      </p>
                    </Link>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">You haven't created any cubes yet.</p>
              <Link
                to="/cubes/new"
                className="inline-block bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
              >
                Create Your First Cube
              </Link>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
