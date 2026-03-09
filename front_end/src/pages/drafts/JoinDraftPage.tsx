import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { draftsApi } from '../../api/drafts'
import Layout from '../../components/Layout'
import { useAuth } from '../../auth/AuthProvider'

export default function JoinDraftPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [draftCode, setDraftCode] = useState('')
  const [password, setPassword]   = useState('')
  const [error, setError]         = useState('')

  const draftId = parseInt(draftCode.trim()) || 0

  const joinMutation = useMutation({
    mutationFn: async () => {
      await draftsApi.joinDraft(draftId, password, user?.id)
      const draft = await draftsApi.getDraft(draftId)
      return draft
    },
    onSuccess: (draft) => {
      localStorage.setItem(`draft_joined_${draftId}`, 'true')
      navigate(`/cubes/${draft.cube_id}/drafts/${draftId}`)
    },
    onError: () => setError('Incorrect password or draft not found. Check the code with your draft organiser.'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!draftId) { setError('Please enter a valid draft code.'); return }
    if (!password) { setError('Please enter the draft password.'); return }
    joinMutation.mutate()
  }

  return (
    <Layout>
      <div className="max-w-md mx-auto px-4 py-16">
        <div className="bg-white rounded-xl shadow-md p-8 space-y-6">

          <div className="text-center">
            <div className="text-4xl mb-3">🎴</div>
            <h1 className="text-2xl font-bold text-gray-900">Join a Draft</h1>
            <p className="mt-2 text-sm text-gray-500">
              Enter the draft code and password provided by your cube organiser.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Draft Code
              </label>
              <input
                type="text"
                value={draftCode}
                onChange={(e) => setDraftCode(e.target.value)}
                placeholder="e.g. 42"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                autoFocus
              />
              <p className="mt-1 text-xs text-gray-400">Your organiser will share this number with you.</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Draft Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md px-4 py-3">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={joinMutation.isPending}
              className="w-full bg-indigo-600 text-white py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {joinMutation.isPending ? 'Verifying…' : 'Join Draft'}
            </button>
          </form>

          <div className="border-t border-gray-100 pt-4 text-xs text-gray-400 text-center">
            The draft code is the number at the end of the draft URL, e.g. <span className="font-mono">/drafts/<strong>42</strong></span>
          </div>
        </div>
      </div>
    </Layout>
  )
}
