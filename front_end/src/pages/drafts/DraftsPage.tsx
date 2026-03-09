import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { draftsApi, type DraftEvent } from '../../api/drafts'
import { cubesApi } from '../../api/cubes'
import Layout from '../../components/Layout'
import { useAuth } from '../../auth/AuthProvider'

export default function DraftsPage() {
  const { id } = useParams<{ id: string }>()
  const cubeId = parseInt(id!)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [draftName, setDraftName] = useState('')
  const [numPlayers, setNumPlayers] = useState<number | ''>('')
  const [password, setPassword] = useState('')
  const [eventType, setEventType] = useState<'casual' | 'hosted'>('casual')
  const [numRounds, setNumRounds] = useState<number | ''>(3)
  const [bestOf, setBestOf] = useState<1 | 3 | 5>(1)
  const [createdDraft, setCreatedDraft] = useState<{ id: number; name: string; password: string } | null>(null)

  const { data: cube } = useQuery({
    queryKey: ['cube', cubeId],
    queryFn: () => cubesApi.getCube(cubeId),
  })

  const { data: drafts = [], isLoading } = useQuery({
    queryKey: ['drafts', cubeId],
    queryFn: () => draftsApi.getDraftsForCube(cubeId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      draftsApi.createDraft({
        cube_id: cubeId,
        password,
        name: draftName || undefined,
        num_players: numPlayers !== '' ? numPlayers : undefined,
        event_type: eventType,
        ...(eventType === 'hosted' ? {
          num_rounds: numRounds !== '' ? numRounds : 3,
          best_of: bestOf,
        } : {}),
      }, user?.id),
    onSuccess: (newDraft) => {
      queryClient.invalidateQueries({ queryKey: ['drafts', cubeId] })
      setShowCreateForm(false)
      setCreatedDraft({ id: newDraft.id, name: newDraft.name ?? `Draft #${newDraft.id}`, password })
      setDraftName('')
      setNumPlayers('')
      setPassword('')
      setEventType('casual')
      setNumRounds(3)
      setBestOf(1)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (draftId: number) => draftsApi.deleteDraft(draftId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['drafts', cubeId] }),
  })

  // ── stats ──────────────────────────────────────────────────────────────
  const totalDecks   = drafts.reduce((n, d) => n + (d.user_decks?.length ?? 0), 0)
  const completedCount = drafts.filter((d) => d.status === 'completed').length

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        {/* breadcrumb */}
        <div className="text-sm text-gray-500 flex items-center gap-1">
          <Link to="/cubes" className="hover:underline">Cubes</Link>
          <span>/</span>
          <Link to={`/cubes/${cubeId}`} className="hover:underline">{cube?.name ?? `Cube #${cubeId}`}</Link>
          <span>/</span>
          <span className="text-gray-800 font-medium">Drafts</span>
        </div>

        {/* header + create button */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Drafts</h1>
          <button
            onClick={() => setShowCreateForm((v) => !v)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
          >
            {showCreateForm ? 'Cancel' : '+ New Draft'}
          </button>
        </div>

        {/* create form */}
        {showCreateForm && (
          <div className="bg-white rounded-lg shadow-md p-5 border border-blue-200 space-y-4">
            <h2 className="font-semibold text-lg">Create New Draft</h2>

            {/* Event type selector */}
            <div className="grid grid-cols-2 gap-3">
              {(['casual', 'hosted'] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setEventType(type)}
                  className={`py-3 px-4 rounded-lg border-2 text-sm font-medium transition-colors ${
                    eventType === type
                      ? 'border-blue-600 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-600 hover:border-blue-300'
                  }`}
                >
                  {type === 'casual' ? '🎲 Casual Draft' : '🏆 Hosted Event'}
                  <div className="mt-1 text-xs font-normal text-gray-500">
                    {type === 'casual'
                      ? 'Free-form logging, no rounds'
                      : 'Swiss rounds, life tracking, standings'}
                  </div>
                </button>
              ))}
            </div>

            {/* Basic fields */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Draft Name</label>
                <input
                  type="text"
                  value={draftName}
                  onChange={(e) => setDraftName(e.target.value)}
                  placeholder="e.g. Friday Night Draft"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Number of Players</label>
                <input
                  type="number"
                  min={2}
                  max={16}
                  value={numPlayers}
                  onChange={(e) => setNumPlayers(e.target.value === '' ? '' : parseInt(e.target.value))}
                  placeholder="8"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password <span className="text-red-500">*</span></label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 6 chars"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>
            </div>

            {/* Hosted-only settings */}
            {eventType === 'hosted' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Number of Rounds</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={numRounds}
                    onChange={(e) => setNumRounds(e.target.value === '' ? '' : parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Match Format</label>
                  <div className="flex gap-2 mt-1">
                    {([1, 3, 5] as const).map((bo) => (
                      <button
                        key={bo}
                        type="button"
                        onClick={() => setBestOf(bo)}
                        className={`flex-1 py-2 rounded-md border text-sm font-medium transition-colors ${
                          bestOf === bo
                            ? 'border-blue-600 bg-blue-600 text-white'
                            : 'border-gray-300 text-gray-600 hover:border-blue-400'
                        }`}
                      >
                        BO{bo}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={() => createMutation.mutate()}
                disabled={!password || password.length < 6 || createMutation.isPending}
                className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 disabled:opacity-50 text-sm"
              >
                {createMutation.isPending ? 'Creating...' : `Create ${eventType === 'hosted' ? 'Hosted Event' : 'Draft'}`}
              </button>
            </div>
            {createMutation.isError && (
              <p className="text-red-600 text-sm">Error creating draft. Please try again.</p>
            )}
          </div>
        )}

        {/* ── Draft created share card ── */}
        {createdDraft && (
          <div className="bg-green-50 border-2 border-green-400 rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🎉</span>
                <div>
                  <div className="font-semibold text-green-800">Draft created: {createdDraft.name}</div>
                  <div className="text-sm text-green-700">Share the code and password with your players</div>
                </div>
              </div>
              <button
                onClick={() => navigate(`/cubes/${cubeId}/drafts/${createdDraft.id}`)}
                className="bg-green-600 text-white px-4 py-2 rounded-md text-sm hover:bg-green-700"
              >
                Open Draft →
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="bg-white rounded-lg border border-green-200 p-4">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Draft Code</div>
                <div className="flex items-center gap-3">
                  <span className="text-3xl font-bold text-gray-900 font-mono">{createdDraft.id}</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(String(createdDraft.id))}
                    className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-1"
                  >
                    Copy
                  </button>
                </div>
                <div className="text-xs text-gray-400 mt-1">Players enter this on the Join Draft page</div>
              </div>
              <div className="bg-white rounded-lg border border-green-200 p-4">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Password</div>
                <div className="flex items-center gap-3">
                  <span className="text-xl font-bold text-gray-900 font-mono tracking-widest">{createdDraft.password}</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(createdDraft.password)}
                    className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-1"
                  >
                    Copy
                  </button>
                </div>
                <div className="text-xs text-gray-400 mt-1">This is the only time the password is shown</div>
              </div>
            </div>
            <button
              onClick={() => setCreatedDraft(null)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* stats bar */}
        {drafts.length > 0 && (
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Total Drafts', value: drafts.length },
              { label: 'Total Decks logged', value: totalDecks },
              { label: 'Completed', value: completedCount },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-lg shadow p-4 text-center">
                <div className="text-2xl font-bold text-blue-700">{s.value}</div>
                <div className="text-sm text-gray-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* draft list */}
        {isLoading ? (
          <p className="text-gray-500">Loading drafts…</p>
        ) : drafts.length === 0 ? (
          <div className="text-center text-gray-500 py-16">
            <p className="text-lg">No drafts yet.</p>
            <p className="text-sm mt-1">Click <strong>+ New Draft</strong> to record your first draft for this cube.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {drafts.map((draft) => (
              <DraftCard
                key={draft.id}
                draft={draft}
                cubeId={cubeId}
                onDelete={() => {
                  if (window.confirm('Delete this draft and all its decks?')) {
                    deleteMutation.mutate(draft.id)
                  }
                }}
              />
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}

// ── DraftCard sub-component ──────────────────────────────────────────────────

function DraftCard({
  draft,
  cubeId,
  onDelete,
}: {
  draft: DraftEvent
  cubeId: number
  onDelete: () => void
}) {
  const deckCount  = draft.user_decks?.length ?? 0
  const dateStr    = new Date(draft.created_at).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
  const isComplete = draft.status === 'completed'

  // Best record
  const winner = draft.user_decks?.reduce<{ name: string; record: string } | null>((best, d) => {
    const wins = d.wins ?? 0
    const bestWins = best ? parseInt(best.record.split('-')[0] ?? '0') : -1
    return wins > bestWins ? { name: d.player_name ?? 'Unknown', record: d.record ?? `${d.wins}-${d.losses}` } : best
  }, null)

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow border border-gray-100">
      <Link to={`/cubes/${cubeId}/drafts/${draft.id}`} className="block p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-gray-900 text-lg truncate">
                {draft.name ?? `Draft #${draft.id}`}
              </h3>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                isComplete ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
              }`}>
                {isComplete ? 'Completed' : 'Active'}
              </span>
              {draft.event_type === 'hosted' && (
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-purple-100 text-purple-700">
                  🏆 Hosted
                </span>
              )}
            </div>
            <div className="mt-1 text-sm text-gray-500 flex flex-wrap gap-4">
              <span>{dateStr}</span>
              {draft.num_players ? <span>{draft.num_players} players</span> : null}
              <span>{deckCount} deck{deckCount !== 1 ? 's' : ''} logged</span>
              {winner ? <span>🏆 {winner.name} ({winner.record})</span> : null}
            </div>
            {draft.ai_summary && (
              <p className="mt-2 text-sm text-gray-600 line-clamp-2 italic">"{draft.ai_summary}"</p>
            )}
          </div>
          <span className="text-blue-600 text-sm shrink-0 mt-1">View →</span>
        </div>
      </Link>
      <div className="border-t border-gray-100 px-5 py-2 flex justify-end">
        <button
          onClick={(e) => { e.preventDefault(); onDelete() }}
          className="text-xs text-red-500 hover:text-red-700"
        >
          Delete draft
        </button>
      </div>
    </div>
  )
}
