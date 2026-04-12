import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../../auth/AuthProvider'
import { cubesApi } from '../../api/cubes'
import { cardsApi } from '../../api/cards'
import Layout from '../../components/Layout'

const cubeSchema = z.object({
  name: z.string().min(1, 'Cube name is required'),
  description: z.string().optional(),
  cardList: z.string().min(1, 'Card list is required'),
})

type CubeFormData = z.infer<typeof cubeSchema>

export default function CreateCubePage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string>('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [cubecobraLink, setCubecobraLink] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CubeFormData>({
    resolver: zodResolver(cubeSchema),
  })

  const createCubeMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; cubecobra_link?: string }) =>
      cubesApi.createCube(data, user!.id),
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to create cube')
      setIsProcessing(false)
    },
  })

  const onSubmit = async (data: CubeFormData) => {
    setError('')
    setIsProcessing(true)

    try {
      // Parse card list (one card per line)
      const cardNames = data.cardList
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0)

      if (cardNames.length === 0) {
        setError('Please enter at least one card')
        setIsProcessing(false)
        return
      }

      // Create the cube first
      const cube = await createCubeMutation.mutateAsync({
        name: data.name,
        description: data.description,
        cubecobra_link: cubecobraLink.trim() || undefined,
      })

      // Bulk-fetch all cards from Scryfall and store them in the DB
      const fetchResult = await cardsApi.bulkFetchAndStoreCards(cardNames)

      // Bulk-add all found cards to the new cube
      let addResult = { added: 0, skipped: 0 }
      if (fetchResult.cards.length > 0) {
        addResult = await cubesApi.bulkAddCardsToCube(
          cube.id,
          fetchResult.cards.map((c) => c.id),
        )
      }

      if (fetchResult.not_found.length > 0) {
        console.warn('Cards not found on Scryfall:', fetchResult.not_found)
      }

      // Invalidate cache and navigate to the new cube, passing upload results
      queryClient.invalidateQueries({ queryKey: ['userCubes', user!.id] })
      navigate(`/cubes/${cube.id}`, {
        state: {
          uploadResult: {
            added: addResult.added,
            notFound: fetchResult.not_found,
          },
        },
      })
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to create cube')
      setIsProcessing(false)
    }
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Create New Cube</h1>

        <div className="bg-white rounded-lg shadow-md p-8">
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Cube Name *
              </label>
              <input
                {...register('name')}
                type="text"
                id="name"
                placeholder="My Awesome Cube"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.name && (
                <p className="text-red-500 text-sm mt-1">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label
                htmlFor="description"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Description
              </label>
              <textarea
                {...register('description')}
                id="description"
                rows={3}
                placeholder="A brief description of your cube"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.description && (
                <p className="text-red-500 text-sm mt-1">{errors.description.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="cubecobraLink" className="block text-sm font-medium text-gray-700 mb-1">
                CubeCobra Link (optional)
              </label>
              <input
                type="url"
                id="cubecobraLink"
                value={cubecobraLink}
                onChange={(e) => setCubecobraLink(e.target.value)}
                placeholder="https://cubecobra.com/cube/overview/..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-gray-500 text-sm mt-1">Link your cube's CubeCobra page if you have one.</p>
            </div>

            <div>
              <label htmlFor="cardList" className="block text-sm font-medium text-gray-700 mb-1">
                Card List * (one card per line)
              </label>
              <textarea
                {...register('cardList')}
                id="cardList"
                rows={15}
                placeholder={'Lightning Bolt\nCounterspell\nSwords to Plowshares\n...'}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              />
              {errors.cardList && (
                <p className="text-red-500 text-sm mt-1">{errors.cardList.message}</p>
              )}
              <p className="text-gray-500 text-sm mt-1">
                Paste your cube list here. Cards will be fetched from Scryfall.
              </p>
            </div>

            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={isProcessing || createCubeMutation.isPending}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {isProcessing ? 'Creating cube...' : 'Create Cube'}
              </button>
              <button
                type="button"
                onClick={() => navigate('/cubes')}
                className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  )
}
