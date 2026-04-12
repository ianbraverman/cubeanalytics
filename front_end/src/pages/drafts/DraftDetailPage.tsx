import { useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { draftsApi, type UserDeck, type DraftParticipant, type DraftSeat, type DraftRound, type DraftPairing } from '../../api/drafts'
import { cubesApi, type CubeCard } from '../../api/cubes'
import Layout from '../../components/Layout'
import { useAuth } from '../../auth/AuthProvider'

// ── helpers ──────────────────────────────────────────────────────────────────

function buildCardMap(cubeCards: CubeCard[]): Map<number, string> {
  const m = new Map<number, string>()
  cubeCards.forEach((cc) => m.set(cc.card_id, cc.card?.name ?? `Card #${cc.card_id}`))
  return m
}

// ── page ──────────────────────────────────────────────────────────────────────

export default function DraftDetailPage() {
  const { id, draftId } = useParams<{ id: string; draftId: string }>()
  const cubeId   = parseInt(id!)
  const eventId  = parseInt(draftId!)
  const queryClient = useQueryClient()
  const { user } = useAuth()

  // ── join state ──
  const joinKey = `draft_joined_${eventId}`
  const [joined, setJoined] = useState(() => localStorage.getItem(joinKey) === 'true')
  const [joinPassword, setJoinPassword] = useState('')
  const [joinError, setJoinError]       = useState('')
  const [showJoinForm, setShowJoinForm] = useState(false)

  const joinMutation = useMutation({
    mutationFn: () => draftsApi.joinDraft(eventId, joinPassword, user?.id),
    onSuccess: () => {
      localStorage.setItem(joinKey, 'true')
      setJoined(true)
      setShowJoinForm(false)
      setJoinError('')
    },
    onError: () => setJoinError('Incorrect password — check with the draft organiser'),
  })

  // ── data ──
  const { data: draft, isLoading } = useQuery({
    queryKey: ['draft', eventId],
    queryFn: () => draftsApi.getDraft(eventId),
  })

  const { data: cubeCards = [] } = useQuery({
    queryKey: ['cubeCards', cubeId],
    queryFn: () => cubesApi.getCubeCards(cubeId),
  })

  const { data: cube } = useQuery({
    queryKey: ['cube', cubeId],
    queryFn: () => cubesApi.getCube(cubeId),
  })

  // Cube owners are automatically participants — no password needed
  const isCubeOwner = !!(user && cube && cube.owner_id === user.id)

  const cardMap = buildCardMap(cubeCards)

  // ── AI mutations ──
  const draftAIMutation = useMutation({
    mutationFn: () => draftsApi.generateDraftAI(eventId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['draft', eventId] }),
  })

  const markCompleteMutation = useMutation({
    mutationFn: () => draftsApi.updateDraft(eventId, { status: 'completed' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['draft', eventId] }),
  })

  // ── empty slot toggle (owner can expand to add a guest deck) ──
  const [openEmptySlot, setOpenEmptySlot] = useState<number | null>(null)

  // ── change password ──
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [changePasswordMsg, setChangePasswordMsg] = useState('')

  const changePasswordMutation = useMutation({
    mutationFn: () => draftsApi.changePassword(eventId, newPassword),
    onSuccess: () => {
      setChangePasswordMsg('Password updated!')
      setNewPassword('')
      setShowChangePassword(false)
    },
  })

  if (isLoading) return <Layout><div className="p-8 text-gray-500">Loading draft…</div></Layout>
  if (!draft)    return <Layout><div className="p-8 text-red-500">Draft not found.</div></Layout>

  const decks = draft.user_decks ?? []
  const isComplete = draft.status === 'completed'

  // The logged-in user's deck for this draft (if they have one)
  const myDeck = user ? decks.find((d) => d.user_id === user.id) : undefined
  // User is considered "in" the draft if they own the cube, joined via password, or already have a deck
  const isParticipant = isCubeOwner || joined || !!myDeck

  // leaderboard: sorted by wins desc
  const sorted = [...decks].sort((a, b) => (b.wins ?? 0) - (a.wins ?? 0))

  // ── Unified casual draft slot list ──
  type CasualSlot =
    | { kind: 'my'; deck?: UserDeck }
    | { kind: 'participant'; participant: DraftParticipant; deck?: UserDeck }
    | { kind: 'guest'; deck: UserDeck }
    | { kind: 'empty'; index: number }

  const casualSlots: CasualSlot[] = []
  if (draft.event_type !== 'hosted') {
    if (user && isParticipant) {
      casualSlots.push({ kind: 'my', deck: myDeck })
    }
    const otherParticipants = (draft.participants ?? []).filter((p) => !user || p.user_id !== user.id)
    const accountedDeckIds = new Set<number>(myDeck ? [myDeck.id] : [])
    otherParticipants.forEach((p) => {
      const deck = decks.find((d) => d.user_id === p.user_id && (!myDeck || d.id !== myDeck.id))
      if (deck) accountedDeckIds.add(deck.id)
      casualSlots.push({ kind: 'participant', participant: p, deck })
    })
    decks.filter((d) => !accountedDeckIds.has(d.id)).forEach((d) => {
      casualSlots.push({ kind: 'guest', deck: d })
    })
    if (isCubeOwner && draft.num_players) {
      const filled = casualSlots.filter((s) => s.kind !== 'empty').length
      const emptyCount = Math.max(0, draft.num_players - filled)
      for (let i = 0; i < emptyCount; i++) {
        casualSlots.push({ kind: 'empty', index: i })
      }
    }
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">

        {/* breadcrumb */}
        <div className="text-sm text-gray-500 flex items-center gap-1 flex-wrap">
          <Link to="/cubes" className="hover:underline">Cubes</Link>
          <span>/</span>
          <Link to={`/cubes/${cubeId}`} className="hover:underline">{cube?.name ?? `Cube #${cubeId}`}</Link>
          <span>/</span>
          <Link to={`/cubes/${cubeId}/drafts`} className="hover:underline">Drafts</Link>
          <span>/</span>
          <span className="text-gray-800 font-medium">{draft.name ?? `Draft #${draft.id}`}</span>
        </div>

        {/* header */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-bold">{draft.name ?? `Draft #${draft.id}`}</h1>
                <span className={`text-sm px-3 py-0.5 rounded-full font-medium ${
                  isComplete ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {isComplete ? 'Completed' : 'Active'}
                </span>
              </div>
              <div className="mt-1 text-sm text-gray-500 flex flex-wrap gap-4">
                <span>{new Date(draft.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
                {draft.num_players ? <span>{draft.num_players} players</span> : null}
                <span>{decks.length} deck{decks.length !== 1 ? 's' : ''} logged</span>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              {!isComplete && draft.event_type !== 'hosted' && (
                <button
                  onClick={() => markCompleteMutation.mutate()}
                  disabled={markCompleteMutation.isPending}
                  className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 text-sm disabled:opacity-50"
                >
                  Mark Complete
                </button>
              )}
              <button
                onClick={() => draftAIMutation.mutate()}
                disabled={draftAIMutation.isPending || decks.length === 0}
                className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 text-sm disabled:opacity-50"
              >
                {draftAIMutation.isPending ? '✨ Generating…' : '✨ AI Draft Summary'}
              </button>

              {isCubeOwner && (
                <button
                  onClick={() => { setShowChangePassword((v) => !v); setChangePasswordMsg('') }}
                  className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 text-sm"
                >
                  🔑 Change Password
                </button>
              )}
            </div>
          </div>

          {/* Change password inline form */}
          {isCubeOwner && showChangePassword && (
            <div className="mt-4 bg-gray-50 border border-gray-200 rounded-lg p-4 flex flex-wrap items-end gap-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  minLength={6}
                  placeholder="Min 6 characters"
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm w-56 focus:outline-none focus:ring-2 focus:ring-gray-400"
                />
              </div>
              <button
                onClick={() => changePasswordMutation.mutate()}
                disabled={newPassword.length < 6 || changePasswordMutation.isPending}
                className="bg-gray-700 text-white px-4 py-2 rounded-md text-sm hover:bg-gray-800 disabled:opacity-50"
              >
                {changePasswordMutation.isPending ? 'Saving…' : 'Update Password'}
              </button>
              <button
                onClick={() => setShowChangePassword(false)}
                className="text-sm text-gray-500 hover:text-gray-700 px-2 py-2"
              >
                Cancel
              </button>
              {changePasswordMsg && <p className="text-sm text-green-600 w-full">{changePasswordMsg}</p>}
            </div>
          )}

          {/* AI Summary */}
          {draft.ai_summary && (
            <div className="mt-4 bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="text-xs font-semibold text-purple-600 uppercase tracking-wide mb-2">✨ AI Draft Narrative</div>
              <div className="prose prose-sm max-w-none text-gray-800 [&>h1]:text-lg [&>h1]:font-bold [&>h1]:mt-4 [&>h1]:mb-2 [&>h2]:text-base [&>h2]:font-bold [&>h2]:mt-3 [&>h2]:mb-1 [&>h3]:text-sm [&>h3]:font-semibold [&>h3]:mt-3 [&>h3]:mb-1 [&>p]:mb-2 [&>hr]:my-3 [&>strong]:font-semibold">
                <ReactMarkdown>{String(draft.ai_summary)}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Draft code + participants */}
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Draft code — only visible to cube owner */}
            {isCubeOwner && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Draft Code</div>
                <div className="flex items-center gap-3">
                  <span className="text-3xl font-bold font-mono text-gray-900">{draft.id}</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(String(draft.id))}
                    className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-1"
                  >
                    Copy
                  </button>
                </div>
                <div className="text-xs text-gray-400 mt-1">Share this with players so they can join via "Join Draft"</div>
              </div>
            )}

            {/* Players panel */}
            <div className={`bg-gray-50 border border-gray-200 rounded-lg p-4 ${!isCubeOwner ? 'sm:col-span-2' : ''}`}>
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Players Joined ({(draft.participants ?? []).length})
              </div>
              {(draft.participants ?? []).length === 0 ? (
                <div className="text-xs text-gray-400">No players have joined yet</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {(draft.participants ?? []).map((p) => (
                    <div key={p.user_id} className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-full px-3 py-1">
                      <div className="w-5 h-5 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xs font-bold">
                        {p.username[0].toUpperCase()}
                      </div>
                      <span className="text-sm text-gray-800">{p.username}</span>
                      {/* show if they have a deck */}
                      {(draft.user_decks ?? []).some((d) => d.user_id === p.user_id) && (
                        <span className="text-xs text-green-600">✓</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <div className="text-xs text-gray-400 mt-2">✓ = deck submitted</div>
            </div>
          </div>
        </div>

        {/* ── Join Draft banner (logged-in, not yet a participant) ── */}
        {user && !isParticipant && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-semibold text-indigo-800">Join this draft as {user.username}</div>
                <div className="text-sm text-indigo-600">Enter the draft password to submit your own deck</div>
              </div>
              {!showJoinForm ? (
                <button
                  onClick={() => setShowJoinForm(true)}
                  className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm hover:bg-indigo-700"
                >
                  Join Draft
                </button>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type="password"
                    value={joinPassword}
                    onChange={(e) => setJoinPassword(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && joinMutation.mutate()}
                    placeholder="Draft password"
                    className="px-3 py-1.5 border border-indigo-300 rounded-md text-sm w-44 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    autoFocus
                  />
                  <button
                    onClick={() => joinMutation.mutate()}
                    disabled={!joinPassword || joinMutation.isPending}
                    className="bg-indigo-600 text-white px-4 py-1.5 rounded-md text-sm hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {joinMutation.isPending ? 'Verifying…' : 'Confirm'}
                  </button>
                  <button onClick={() => setShowJoinForm(false)} className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
                </div>
              )}
            </div>
            {joinError && <p className="mt-2 text-sm text-red-600">{joinError}</p>}
          </div>
        )}

        {/* ── Hosted event flow ── */}
        {draft.event_type === 'hosted' && isParticipant && (
          <HostedEventView
            draftId={eventId}
            draft={draft}
            cube={cube}
            userId={user?.id}
            isCubeOwner={isCubeOwner}
            cardMap={cardMap}
            cubeCards={cubeCards}
          />
        )}



        {/* standings (casual only) */}
        {draft.event_type !== 'hosted' && sorted.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-5">
            <h2 className="font-semibold text-lg mb-3">Standings</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-gray-500">
                    <th className="py-2 pr-4">#</th>
                    <th className="py-2 pr-4">Player</th>
                    <th className="py-2 pr-4">Deck</th>
                    <th className="py-2 pr-4 text-center">W</th>
                    <th className="py-2 pr-4 text-center">L</th>
                    <th className="py-2">Record</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((deck, i) => (
                    <tr key={deck.id} className={`border-b border-gray-100 ${i === 0 ? 'font-semibold' : ''}`}>
                      <td className="py-2 pr-4 text-gray-400">{i === 0 ? '🏆' : i + 1}</td>
                      <td className="py-2 pr-4">{deck.player_name ?? '—'}</td>
                      <td className="py-2 pr-4 text-gray-600">{deck.deck_name ?? '—'}</td>
                      <td className="py-2 pr-4 text-center text-green-700">{deck.wins}</td>
                      <td className="py-2 pr-4 text-center text-red-600">{deck.losses}</td>
                      <td className="py-2 font-mono">{deck.record ?? `${deck.wins}-${deck.losses}`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Casual draft: unified deck slots ── */}
        {draft.event_type !== 'hosted' && (
          casualSlots.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {casualSlots.map((slot) => {
                if (slot.kind === 'my') {
                  return (
                    <div key="my" className="bg-white rounded-lg shadow-md border-2 border-indigo-200 overflow-hidden">
                      <div className="bg-indigo-600 text-white px-5 py-3 flex items-center justify-between">
                        <div className="font-semibold">🧑‍💻 Your Deck — {user!.username}</div>
                        {slot.deck && <div className="text-indigo-200 text-sm">{slot.deck.wins}–{slot.deck.losses}</div>}
                      </div>
                      {slot.deck ? (
                        <DeckCard deck={slot.deck} draftId={eventId} cardMap={cardMap}
                          onUpdated={() => queryClient.invalidateQueries({ queryKey: ['draft', eventId] })}
                          userId={user?.id} isCubeOwner={isCubeOwner} isMyDeck={true} />
                      ) : (
                        <div className="p-5">
                          <p className="text-sm text-gray-500 mb-4">Submit your deck below.</p>
                          <AddDeckForm draftId={eventId} cubeCards={cubeCards} userId={user!.id}
                            lockedPlayerName={user!.username}
                            onCreated={() => queryClient.invalidateQueries({ queryKey: ['draft', eventId] })} />
                        </div>
                      )}
                    </div>
                  )
                }
                if (slot.kind === 'participant') {
                  return (
                    <div key={`p-${slot.participant.user_id}`} className="bg-white rounded-lg shadow-md overflow-hidden">
                      <div className="bg-gray-50 border-b px-5 py-3 flex items-center justify-between">
                        <div className="font-medium text-gray-800">👤 {slot.participant.username}</div>
                        {slot.deck
                          ? <div className="text-sm text-gray-500">{slot.deck.wins}–{slot.deck.losses}</div>
                          : <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">Deck pending</span>
                        }
                      </div>
                      {slot.deck ? (
                        <DeckCard deck={slot.deck} draftId={eventId} cardMap={cardMap}
                          onUpdated={() => queryClient.invalidateQueries({ queryKey: ['draft', eventId] })}
                          userId={user?.id} isCubeOwner={isCubeOwner} isMyDeck={false} />
                      ) : isCubeOwner ? (
                        <div className="p-4">
                          <AddDeckForm draftId={eventId} cubeCards={cubeCards}
                            defaultPlayerName={slot.participant.username}
                            onCreated={() => queryClient.invalidateQueries({ queryKey: ['draft', eventId] })} />
                        </div>
                      ) : (
                        <div className="px-5 py-8 text-center text-gray-400 text-sm">Waiting for player to submit their deck…</div>
                      )}
                    </div>
                  )
                }
                if (slot.kind === 'guest') {
                  return (
                    <div key={`g-${slot.deck.id}`} className="bg-white rounded-lg shadow-md overflow-hidden">
                      <div className="bg-gray-50 border-b px-5 py-3 flex items-center justify-between">
                        <div className="font-medium text-gray-800">👤 {slot.deck.player_name ?? 'Guest Player'}</div>
                        <div className="text-sm text-gray-500">{slot.deck.wins}–{slot.deck.losses}</div>
                      </div>
                      <DeckCard deck={slot.deck} draftId={eventId} cardMap={cardMap}
                        onUpdated={() => queryClient.invalidateQueries({ queryKey: ['draft', eventId] })}
                        userId={user?.id} isCubeOwner={isCubeOwner} isMyDeck={false} />
                    </div>
                  )
                }
                if (slot.kind === 'empty') {
                  const isOpen = openEmptySlot === slot.index
                  return (
                    <div key={`e-${slot.index}`} className="bg-white rounded-lg shadow-md border-2 border-dashed border-gray-200 overflow-hidden">
                      <div className="bg-gray-50 border-b px-5 py-3 flex items-center justify-between">
                        <div className="text-gray-400 font-medium">Open Slot</div>
                        <button
                          onClick={() => setOpenEmptySlot(isOpen ? null : slot.index)}
                          className="text-xs text-blue-600 hover:text-blue-800 border border-blue-200 rounded px-2 py-1"
                        >
                          {isOpen ? '✕ Cancel' : '+ Add Deck'}
                        </button>
                      </div>
                      {isOpen ? (
                        <div className="p-4">
                          <AddDeckForm draftId={eventId} cubeCards={cubeCards}
                            onCreated={() => {
                              queryClient.invalidateQueries({ queryKey: ['draft', eventId] })
                              setOpenEmptySlot(null)
                            }} />
                        </div>
                      ) : (
                        <div className="px-5 py-8 text-center text-gray-300 text-sm">Click "+ Add Deck" to enter a player's deck</div>
                      )}
                    </div>
                  )
                }
                return null
              })}
            </div>
          ) : (
            <div className="text-center text-gray-400 py-12 bg-white rounded-lg shadow">
              No decks logged yet.
            </div>
          )
        )}

        {/* ── Quick draft feedback (casual) ── */}
        {draft.event_type !== 'hosted' && (isParticipant || isCubeOwner) && (
          <PostDraftSection
            draftId={eventId}
            userId={user?.id}
            isCubeOwner={isCubeOwner}
            draft={draft as unknown as Record<string, unknown>}
            rounds={[]}
            cardMap={cardMap}
          />
        )}
      </div>
    </Layout>
  )
}

// ── AddDeckForm ───────────────────────────────────────────────────────────────

function CardListEditor({
  label,
  icon,
  ids,
  onChange,
  cardMap,
}: {
  label: string
  icon: string
  ids: number[]
  onChange: (ids: number[]) => void
  cardMap: Map<number, string>
}) {
  const [addSearch, setAddSearch] = useState('')
  const entries = Array.from(cardMap.entries())
    .filter(([id, name]) => !ids.includes(id) && name.toLowerCase().includes(addSearch.toLowerCase()))
    .sort((a, b) => a[1].localeCompare(b[1]))

  return (
    <div>
      <div className="text-sm font-medium text-gray-700 mb-1.5">{icon} {label} ({ids.length})</div>
      <div className="border border-gray-200 rounded-md max-h-44 overflow-y-auto divide-y bg-white">
        {ids.length === 0 ? (
          <div className="p-3 text-xs text-gray-400 text-center italic">None — use the search below to add cards</div>
        ) : ids.map((id) => (
          <div key={id} className="flex items-center justify-between px-3 py-1 text-sm hover:bg-gray-50">
            <span>{cardMap.get(id) ?? `#${id}`}</span>
            <button
              onClick={() => onChange(ids.filter((x) => x !== id))}
              className="text-red-400 hover:text-red-600 text-xs font-bold ml-2 flex-shrink-0"
            >✕</button>
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-1">
        <input
          value={addSearch}
          onChange={(e) => setAddSearch(e.target.value)}
          placeholder={`Search to add to ${label.toLowerCase()}…`}
          className="flex-1 text-xs px-2 py-1.5 border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-indigo-400"
        />
      </div>
      {addSearch && (
        <div className="border border-gray-200 rounded mt-0.5 max-h-32 overflow-y-auto divide-y bg-white shadow-sm">
          {entries.slice(0, 30).map(([id, name]) => (
            <button
              key={id}
              onClick={() => { onChange([...ids, id]); setAddSearch('') }}
              className="w-full text-left px-3 py-1 text-xs hover:bg-indigo-50 hover:text-indigo-700"
            >{name}</button>
          ))}
          {entries.length === 0 && (
            <div className="px-3 py-2 text-xs text-gray-400">No matching cards</div>
          )}
        </div>
      )}
    </div>
  )
}

function AddDeckForm({
  draftId,
  cubeCards,
  userId,
  defaultPlayerName,
  lockedPlayerName,
  onCreated,
}: {
  draftId: number
  cubeCards: CubeCard[]
  userId?: number
  defaultPlayerName?: string
  lockedPlayerName?: string
  onCreated: () => void
}) {
  // build card map from cubeCards
  const cardMap = buildCardMap(cubeCards)

  // form fields
  const [playerName, setPlayerName] = useState(lockedPlayerName ?? defaultPlayerName ?? '')
  const [deckName, setDeckName]     = useState('')
  const [wins, setWins]             = useState(0)
  const [losses, setLosses]         = useState(0)

  // photos
  const [deckFile, setDeckFile]       = useState<File | null>(null)
  const [poolFile, setPoolFile]       = useState<File | null>(null)
  const [deckPreview, setDeckPreview] = useState<string | null>(null)
  const [poolPreview, setPoolPreview] = useState<string | null>(null)
  const deckFileRef = useRef<HTMLInputElement>(null)
  const poolFileRef = useRef<HTMLInputElement>(null)
  const [isDragOverDeck, setIsDragOverDeck] = useState(false)
  const [isDragOverPool, setIsDragOverPool] = useState(false)

  // analyze / staged phase
  type Phase = 'input' | 'staged'
  const [phase, setPhase]           = useState<Phase>('input')
  const [createdDeckId, setCreatedDeckId] = useState<number | null>(null)
  const [stagedDeckIds, setStagedDeckIds] = useState<number[]>([])
  const [stagedPoolIds, setStagedPoolIds] = useState<number[]>([])
  const [stagedSideIds, setStagedSideIds] = useState<number[]>([])
  const [analyzeError, setAnalyzeError]   = useState<string | null>(null)

  // manual card picker (used when no photos)
  const [search, setSearch]             = useState('')
  const [manualDeckIds, setManualDeckIds] = useState<number[]>([])
  const [manualPoolIds, setManualPoolIds] = useState<number[]>([])

  // ── mutations ──────────────────────────────────────────────────────────────

  // Step 1: create deck + analyze photos → enter staged phase
  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const deck = await draftsApi.createDeck(draftId, {
        draft_event_id: draftId,
        user_id:        userId,
        player_name:    playerName || undefined,
        deck_name:      deckName   || undefined,
        wins,
        losses,
      })
      setCreatedDeckId(deck.id)
      const result = await draftsApi.analyzePhotos(draftId, deck.id, deckFile!, poolFile)
      return result
    },
    onSuccess: (data) => {
      setAnalyzeError(null)
      const nameToId = new Map<string, number>()
      cardMap.forEach((name, id) => nameToId.set(name.toLowerCase(), id))
      const matchIds = (names: string[]) =>
        names.map((n) => nameToId.get(n.toLowerCase())).filter((id): id is number => id !== undefined)
      setStagedDeckIds(matchIds(data.deck_identified))
      setStagedPoolIds(matchIds(data.pool_identified))
      setStagedSideIds(matchIds(data.sideboard_identified ?? []))
      setPhase('staged')
    },
    onError: () => setAnalyzeError('Analysis failed — please try again or save manually'),
  })

  // Step 2 (after staged editing): update deck with confirmed card lists
  const confirmMutation = useMutation({
    mutationFn: () =>
      draftsApi.updateDeck(draftId, createdDeckId!, {
        deck_cards:      stagedDeckIds,
        full_pool_cards: stagedPoolIds,
        sideboard_cards: stagedSideIds,
      }),
    onSuccess: onCreated,
  })

  // No-photos path: just create deck with manual card selection
  const createMutation = useMutation({
    mutationFn: () =>
      draftsApi.createDeck(draftId, {
        draft_event_id:  draftId,
        user_id:         userId,
        player_name:     playerName || undefined,
        deck_name:       deckName   || undefined,
        deck_cards:      manualDeckIds,
        full_pool_cards: manualPoolIds.length ? manualPoolIds : undefined,
        wins,
        losses,
      }),
    onSuccess: onCreated,
  })

  const filtered = cubeCards
    .filter((cc) => (cc.card?.name?.toLowerCase() ?? '').includes(search.toLowerCase()))

  const toggleCard = (cardId: number, inDeck: boolean) => {
    const setter = inDeck ? setManualDeckIds : setManualPoolIds
    setter((prev) =>
      prev.includes(cardId) ? prev.filter((id) => id !== cardId) : [...prev, cardId]
    )
  }

  // ── Staged review phase ────────────────────────────────────────────────────
  if (phase === 'staged') {
    return (
      <div className="bg-white rounded-lg shadow-md p-5 border border-green-200 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="font-semibold text-lg">Review Identified Cards</h2>
            <p className="text-xs text-gray-500 mt-0.5">Add or remove cards before confirming the deck</p>
          </div>
          <button onClick={() => setPhase('input')} className="text-xs text-gray-400 hover:text-gray-600">← Back</button>
        </div>

        <CardListEditor label="Deck" icon="🃏" ids={stagedDeckIds} onChange={setStagedDeckIds} cardMap={cardMap} />
        <CardListEditor label="Full Pool" icon="🎴" ids={stagedPoolIds} onChange={setStagedPoolIds} cardMap={cardMap} />
        <CardListEditor label="Sideboard" icon="📋" ids={stagedSideIds} onChange={setStagedSideIds} cardMap={cardMap} />

        <div className="flex justify-end pt-2">
          <button
            onClick={() => confirmMutation.mutate()}
            disabled={confirmMutation.isPending}
            className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 text-sm disabled:opacity-50"
          >
            {confirmMutation.isPending ? 'Saving…' : 'Confirm & Save Deck'}
          </button>
        </div>
      </div>
    )
  }

  // ── Input phase ────────────────────────────────────────────────────────────
  return (
    <div className="bg-white rounded-lg shadow-md p-5 border border-blue-200 space-y-4">
      <h2 className="font-semibold text-lg">Add Deck</h2>

      {/* form fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Player Name</label>
          <input
            value={playerName}
            onChange={(e) => { if (!lockedPlayerName) setPlayerName(e.target.value) }}
            readOnly={!!lockedPlayerName}
            className={`w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${lockedPlayerName ? 'border-gray-200 bg-gray-50 text-gray-500 cursor-default' : 'border-gray-300'}`}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Deck Name</label>
          <input value={deckName} onChange={(e) => setDeckName(e.target.value)}
            placeholder="e.g. UW Skies"
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Wins</label>
          <input type="number" min={0} value={wins} onChange={(e) => setWins(parseInt(e.target.value) || 0)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Losses</label>
          <input type="number" min={0} value={losses} onChange={(e) => setLosses(parseInt(e.target.value) || 0)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      {/* photo upload */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Photos for AI Card Recognition <span className="text-gray-400 font-normal">(optional — upload deck photo, or both to analyse)</span>
        </label>
        <div className="grid grid-cols-2 gap-3">
          <div
            onClick={() => deckFileRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setIsDragOverDeck(true) }}
            onDragEnter={(e) => { e.preventDefault(); setIsDragOverDeck(true) }}
            onDragLeave={() => setIsDragOverDeck(false)}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragOverDeck(false)
              const f = e.dataTransfer.files?.[0]
              if (f && f.type.startsWith('image/')) { setDeckFile(f); setDeckPreview(URL.createObjectURL(f)) }
            }}
            className={`relative h-28 rounded-lg border-2 border-dashed cursor-pointer transition-colors flex items-center justify-center overflow-hidden ${
              isDragOverDeck ? 'border-indigo-500 bg-indigo-100' : 'border-gray-300 hover:border-indigo-400 hover:bg-indigo-50'
            }`}
          >
            {deckPreview ? (
              <>
                <img src={deckPreview} alt="Deck" className="absolute inset-0 w-full h-full object-cover rounded-lg" />
                <div className="absolute inset-0 bg-black/30 flex items-center justify-center rounded-lg">
                  <span className="text-white text-xs font-medium">✓ Deck Photo</span>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-400 pointer-events-none">
                <div className="text-2xl mb-1">🃏</div>
                <div className="text-xs font-medium">Deck Photo</div>
                <div className="text-xs">click or drag to upload</div>
              </div>
            )}
          </div>
          <div
            onClick={() => poolFileRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setIsDragOverPool(true) }}
            onDragEnter={(e) => { e.preventDefault(); setIsDragOverPool(true) }}
            onDragLeave={() => setIsDragOverPool(false)}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragOverPool(false)
              const f = e.dataTransfer.files?.[0]
              if (f && f.type.startsWith('image/')) { setPoolFile(f); setPoolPreview(URL.createObjectURL(f)) }
            }}
            className={`relative h-28 rounded-lg border-2 border-dashed cursor-pointer transition-colors flex items-center justify-center overflow-hidden ${
              isDragOverPool ? 'border-indigo-500 bg-indigo-100' : 'border-gray-300 hover:border-indigo-400 hover:bg-indigo-50'
            }`}
          >
            {poolPreview ? (
              <>
                <img src={poolPreview} alt="Pool" className="absolute inset-0 w-full h-full object-cover rounded-lg" />
                <div className="absolute inset-0 bg-black/30 flex items-center justify-center rounded-lg">
                  <span className="text-white text-xs font-medium">✓ Pool Photo</span>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-400 pointer-events-none">
                <div className="text-2xl mb-1">🎴</div>
                <div className="text-xs font-medium">Full Pool Photo</div>
                <div className="text-xs">click or drag to upload</div>
              </div>
            )}
          </div>
        </div>
        {analyzeError && <p className="mt-1 text-xs text-red-600">{analyzeError}</p>}
        <input ref={deckFileRef} type="file" accept="image/*" className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) { setDeckFile(f); setDeckPreview(URL.createObjectURL(f)) }
            e.target.value = ''
          }}
        />
        <input ref={poolFileRef} type="file" accept="image/*" className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) { setPoolFile(f); setPoolPreview(URL.createObjectURL(f)) }
            e.target.value = ''
          }}
        />
      </div>

      {/* If deck photo uploaded: prompt to analyse */}
      {deckFile && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 flex items-center justify-between gap-3">
          <p className="text-xs text-indigo-700 font-medium">
            {poolFile ? '📷 Both photos ready — click Analyse to identify cards' : '📷 Deck photo ready — pool photo is optional'}
          </p>
          <button
            onClick={() => analyzeMutation.mutate()}
            disabled={analyzeMutation.isPending}
            className="bg-indigo-600 text-white px-4 py-1.5 rounded text-xs font-medium hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
          >
            {analyzeMutation.isPending ? '🔍 Analysing…' : '🔍 Analyse Photos'}
          </button>
        </div>
      )}

      {/* manual card picker (shown when not using photos) */}
      {!deckFile && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Select Cards Manually — Deck ({manualDeckIds.length}) · Pool ({manualPoolIds.length})
          </label>
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search cards…"
            className="w-full mb-2 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-md divide-y">
            {filtered.slice(0, 100).map((cc) => {
              const inDeck = manualDeckIds.includes(cc.card_id)
              const inPool = manualPoolIds.includes(cc.card_id)
              return (
                <div key={cc.card_id} className="flex items-center justify-between px-3 py-1 text-sm hover:bg-gray-50">
                  <span className={inDeck ? 'font-medium text-blue-700' : inPool ? 'text-gray-500' : ''}>
                    {cc.card?.name ?? `#${cc.card_id}`}
                  </span>
                  <div className="flex gap-2">
                    <button onClick={() => toggleCard(cc.card_id, true)}
                      className={`text-xs px-2 py-0.5 rounded ${inDeck ? 'bg-blue-600 text-white' : 'bg-gray-100 hover:bg-blue-100'}`}>
                      Deck
                    </button>
                    <button onClick={() => toggleCard(cc.card_id, false)}
                      className={`text-xs px-2 py-0.5 rounded ${inPool ? 'bg-gray-600 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}>
                      Pool
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* save without photos */}
      {!deckFile && (
        <div className="flex justify-end">
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 text-sm disabled:opacity-50"
          >
            {createMutation.isPending ? 'Saving…' : 'Save Deck'}
          </button>
        </div>
      )}
    </div>
  )
}

// ── DeckCard ──────────────────────────────────────────────────────────────────

function DeckCard({
  deck,
  draftId,
  cardMap,
  onUpdated,
  userId,
  isCubeOwner = false,
  isMyDeck = false,
}: {
  deck: UserDeck
  draftId: number
  cardMap: Map<number, string>
  onUpdated: () => void
  userId?: number
  isCubeOwner?: boolean
  isMyDeck?: boolean
}) {
  // sync state with deck prop when deck changes
  const [editing, setEditing]         = useState(false)
  const [wins, setWins]               = useState(deck.wins)
  const [losses, setLosses]           = useState(deck.losses)
  const [playerName, setPlayerName]   = useState(deck.player_name ?? '')
  const [deckName, setDeckName]       = useState(deck.deck_name ?? '')
  // photos (for re-analyzing an existing deck)
  const [deckFile, setDeckFile]       = useState<File | null>(null)
  const [poolFile, setPoolFile]       = useState<File | null>(null)
  const [deckPreview, setDeckPreview] = useState<string | null>(null)
  const [poolPreview, setPoolPreview] = useState<string | null>(null)
  // staged analysis results (edit before saving)
  const [analysisMsg, setAnalysisMsg] = useState<string | null>(null)
  const [stagedDeckIds, setStagedDeckIds] = useState<number[] | null>(null)
  const [stagedPoolIds, setStagedPoolIds] = useState<number[] | null>(null)
  const [stagedSideIds, setStagedSideIds] = useState<number[] | null>(null)
  // local edit-mode lists
  const [localDeckIds, setLocalDeckIds] = useState<number[]>([])
  const [localPoolIds, setLocalPoolIds] = useState<number[]>([])
  const [localSideIds, setLocalSideIds] = useState<number[]>([])
  const deckFileRef = useRef<HTMLInputElement>(null)
  const poolFileRef = useRef<HTMLInputElement>(null)

  // ── mutations ──────────────────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof draftsApi.updateDeck>[2]) =>
      draftsApi.updateDeck(draftId, deck.id, payload),
    onSuccess: () => {
      setEditing(false)
      setStagedDeckIds(null); setStagedPoolIds(null); setStagedSideIds(null)
      setAnalysisMsg(null)
      onUpdated()
    },
  })

  const aiMutation = useMutation({
    mutationFn: () => draftsApi.generateDeckAI(draftId, deck.id),
    onSuccess: onUpdated,
  })

  const analyzePhotosMutation = useMutation({
    mutationFn: () => {
      if (!deckFile || !poolFile) throw new Error('Both photos required')
      return draftsApi.analyzePhotos(draftId, deck.id, deckFile, poolFile)
    },
    onSuccess: (data) => {
      const nameToId = new Map<string, number>()
      cardMap.forEach((name, id) => nameToId.set(name.toLowerCase(), id))
      const matchIds = (names: string[]) =>
        names.map((n) => nameToId.get(n.toLowerCase())).filter((id): id is number => id !== undefined)
      const deckIds = matchIds(data.deck_identified)
      const poolIds = matchIds(data.pool_identified)
      const sideIds = matchIds(data.sideboard_identified ?? [])
      setStagedDeckIds(deckIds)
      setStagedPoolIds(poolIds)
      setStagedSideIds(sideIds)
      setAnalysisMsg(
        deckIds.length || poolIds.length
          ? `✓ ${deckIds.length} deck · ${poolIds.length} pool · ${sideIds.length} sideboard identified — edit below then save`
          : '⚠ No cards identified — check photo quality',
      )
    },
    onError: () => setAnalysisMsg('Analysis failed — try again'),
  })

  const deleteMutation = useMutation({
    mutationFn: () => draftsApi.deleteDeck(draftId, deck.id),
    onSuccess: onUpdated,
  })

  // ── per-slot feedback ─────────────────────────────────────────────────────
  const [fbRating, setFbRating] = useState<number | ''>(5)
  const [fbThoughts, setFbThoughts] = useState('')
  const [fbStandout, setFbStandout] = useState('')
  const [fbUnderperformer, setFbUnderperformer] = useState('')
  const [fbRecs, setFbRecs] = useState('')
  const [fbCardsToAdd, setFbCardsToAdd] = useState('')
  const [fbCardsToCut, setFbCardsToCut] = useState('')
  const [fbSubmitted, setFbSubmitted] = useState(false)

  const [showOwnerFbForm, setShowOwnerFbForm] = useState(false)
  const [ownerFbRating, setOwnerFbRating] = useState<number | ''>(5)
  const [ownerFbThoughts, setOwnerFbThoughts] = useState('')
  const [ownerFbStandout, setOwnerFbStandout] = useState('')
  const [ownerFbUnderperformer, setOwnerFbUnderperformer] = useState('')
  const [ownerFbRecs, setOwnerFbRecs] = useState('')
  const [ownerFbCardsToAdd, setOwnerFbCardsToAdd] = useState('')
  const [ownerFbCardsToCut, setOwnerFbCardsToCut] = useState('')
  const [ownerFbSaved, setOwnerFbSaved] = useState(false)

  const fbNameToId = new Map<string, number>()
  cardMap.forEach((name, id) => fbNameToId.set(name.toLowerCase(), id))
  const parseFbCardNames = (text: string) =>
    text.split(',').map((s) => s.trim()).filter(Boolean)
      .map((n) => fbNameToId.get(n.toLowerCase())).filter((id): id is number => id !== undefined)

  const fbMutation = useMutation({
    mutationFn: () => draftsApi.submitPostDraftFeedback(draftId, {
      overall_rating: fbRating !== '' ? fbRating : undefined,
      overall_thoughts: fbThoughts || undefined,
      standout_card_ids: parseFbCardNames(fbStandout).length ? parseFbCardNames(fbStandout) : undefined,
      underperformer_card_ids: parseFbCardNames(fbUnderperformer).length ? parseFbCardNames(fbUnderperformer) : undefined,
      recommendations_for_owner: fbRecs || undefined,
      cards_to_add: fbCardsToAdd || undefined,
      cards_to_cut: fbCardsToCut || undefined,
    }, userId),
    onSuccess: () => setFbSubmitted(true),
  })

  const ownerFbMutation = useMutation({
    mutationFn: () => draftsApi.submitPostDraftFeedback(draftId, {
      player_name: deck.player_name?.trim() || undefined,
      overall_rating: ownerFbRating !== '' ? ownerFbRating : undefined,
      overall_thoughts: ownerFbThoughts || undefined,
      standout_card_ids: parseFbCardNames(ownerFbStandout).length ? parseFbCardNames(ownerFbStandout) : undefined,
      underperformer_card_ids: parseFbCardNames(ownerFbUnderperformer).length ? parseFbCardNames(ownerFbUnderperformer) : undefined,
      recommendations_for_owner: ownerFbRecs || undefined,
      cards_to_add: ownerFbCardsToAdd || undefined,
      cards_to_cut: ownerFbCardsToCut || undefined,
    }),
    onSuccess: () => setOwnerFbSaved(true),
  })

  // ── derived display values ─────────────────────────────────────────────────
  // In edit mode use local lists; otherwise use staged (from analyze) or saved
  const viewDeckIds = deck.deck_cards ?? []
  const viewPoolIds = deck.full_pool_cards ?? []
  const viewSideIds = deck.sideboard_cards ?? []

  const enterEdit = () => {
    setLocalDeckIds(stagedDeckIds ?? viewDeckIds)
    setLocalPoolIds(stagedPoolIds ?? viewPoolIds)
    setLocalSideIds(stagedSideIds ?? viewSideIds)
    setEditing(true)
  }

  return (
    <div className="bg-white rounded-lg shadow border border-gray-100 flex flex-col overflow-hidden">

      {/* ── photo upload section ───────────────────────────────────────────── */}
      <div className="border-b border-gray-200 bg-gray-50">
        <div className="grid grid-cols-2 gap-0 divide-x divide-gray-200">
          {/* Deck photo */}
          <div onClick={() => deckFileRef.current?.click()} className="cursor-pointer group relative">
            {deckPreview || deck.deck_photo_url ? (
              <div className="relative">
                <img src={deckPreview ?? `http://localhost:8000${deck.deck_photo_url}`} alt="Deck" className="w-full h-32 object-cover" />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <span className="text-white text-xs font-medium">Change Deck Photo</span>
                </div>
              </div>
            ) : (
              <div className="h-32 flex flex-col items-center justify-center text-gray-400 hover:bg-gray-100 transition-colors">
                <div className="text-2xl mb-1">🃏</div>
                <div className="text-xs font-medium">Deck Photo</div>
                <div className="text-xs opacity-70">click to select</div>
              </div>
            )}
            {deckFile && <div className="absolute top-1 right-1 bg-green-500 text-white text-xs px-1.5 py-0.5 rounded-full">✓</div>}
          </div>
          {/* Pool photo */}
          <div onClick={() => poolFileRef.current?.click()} className="cursor-pointer group relative">
            {poolPreview || deck.pool_photo_url ? (
              <div className="relative">
                <img src={poolPreview ?? `http://localhost:8000${deck.pool_photo_url}`} alt="Pool" className="w-full h-32 object-cover" />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <span className="text-white text-xs font-medium">Change Pool Photo</span>
                </div>
              </div>
            ) : (
              <div className="h-32 flex flex-col items-center justify-center text-gray-400 hover:bg-gray-100 transition-colors">
                <div className="text-2xl mb-1">🎴</div>
                <div className="text-xs font-medium">Full Pool Photo</div>
                <div className="text-xs opacity-70">click to select</div>
              </div>
            )}
            {poolFile && <div className="absolute top-1 right-1 bg-green-500 text-white text-xs px-1.5 py-0.5 rounded-full">✓</div>}
          </div>
        </div>

        {/* Analyse button */}
        {(deckFile || poolFile) && (
          <div className="px-3 py-2 flex items-center gap-2 border-t border-gray-200">
            <button
              onClick={() => analyzePhotosMutation.mutate()}
              disabled={!deckFile || !poolFile || analyzePhotosMutation.isPending}
              className="flex-1 bg-indigo-600 text-white text-xs py-1.5 rounded font-medium hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {analyzePhotosMutation.isPending ? '🔍 Analysing…' : !deckFile ? 'Select deck photo first' : !poolFile ? 'Select pool photo first' : '🔍 Analyse Both Photos'}
            </button>
            <button onClick={() => { setDeckFile(null); setPoolFile(null); setDeckPreview(null); setPoolPreview(null) }} className="text-xs text-gray-400 hover:text-gray-600">Clear</button>
          </div>
        )}

        {/* Analysis result message */}
        {analysisMsg && (
          <div className="px-3 pb-2 pt-1 space-y-1.5">
            <p className={`text-xs font-medium ${analysisMsg.startsWith('✓') ? 'text-green-700' : 'text-amber-600'}`}>{analysisMsg}</p>
            {(stagedDeckIds !== null) && (
              <div className="flex gap-2">
                <button
                  onClick={() => updateMutation.mutate({ deck_cards: stagedDeckIds, full_pool_cards: stagedPoolIds ?? [], sideboard_cards: stagedSideIds ?? [] })}
                  disabled={updateMutation.isPending}
                  className="bg-blue-600 text-white text-xs px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
                >Save Identified Cards</button>
                <button
                  onClick={() => enterEdit()}
                  className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-1"
                >Edit Before Saving</button>
                <button
                  onClick={() => { setStagedDeckIds(null); setStagedPoolIds(null); setStagedSideIds(null); setAnalysisMsg(null) }}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >Discard</button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* hidden file inputs */}
      <input ref={deckFileRef} type="file" accept="image/*" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) { setDeckFile(f); setDeckPreview(URL.createObjectURL(f)) }; e.target.value = '' }}
      />
      <input ref={poolFileRef} type="file" accept="image/*" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) { setPoolFile(f); setPoolPreview(URL.createObjectURL(f)) }; e.target.value = '' }}
      />

      {/* ── body ──────────────────────────────────────────────────────────── */}
      <div className="p-4 flex-1 space-y-4">

        {editing ? (
          /* ── Edit mode ──────────────────────────────────────────────────── */
          <div className="space-y-4">
            {/* Name / record fields */}
            <div className="space-y-2">
              <input value={playerName} onChange={(e) => setPlayerName(e.target.value)}
                placeholder="Player name"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-400" />
              <input value={deckName} onChange={(e) => setDeckName(e.target.value)}
                placeholder="Deck name"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-400" />
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 w-10">Wins</label>
                <input type="number" value={wins} min={0} onChange={(e) => setWins(parseInt(e.target.value) || 0)}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm" />
                <label className="text-xs text-gray-500 w-12 ml-2">Losses</label>
                <input type="number" value={losses} min={0} onChange={(e) => setLosses(parseInt(e.target.value) || 0)}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm" />
              </div>
            </div>

            {/* Card list editors */}
            <CardListEditor label="Deck" icon="🃏" ids={localDeckIds} onChange={setLocalDeckIds} cardMap={cardMap} />
            <CardListEditor label="Full Pool" icon="🎴" ids={localPoolIds} onChange={setLocalPoolIds} cardMap={cardMap} />
            <CardListEditor label="Sideboard" icon="📋" ids={localSideIds} onChange={setLocalSideIds} cardMap={cardMap} />

            <div className="flex gap-2 pt-1">
              <button
                onClick={() => updateMutation.mutate({ player_name: playerName, deck_name: deckName, wins, losses, deck_cards: localDeckIds, full_pool_cards: localPoolIds, sideboard_cards: localSideIds })}
                disabled={updateMutation.isPending}
                className="bg-blue-600 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50"
              >{updateMutation.isPending ? 'Saving…' : 'Save Changes'}</button>
              <button onClick={() => setEditing(false)} className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
            </div>
          </div>
        ) : (
          /* ── View mode ──────────────────────────────────────────────────── */
          <>
            {/* Header row */}
            <div className="flex items-start justify-between">
              <div>
                <div className="font-semibold text-gray-900">{deck.player_name ?? 'Unknown Player'}</div>
                <div className="text-sm text-gray-500">{deck.deck_name ?? 'Unnamed Deck'}</div>
              </div>
              <div className="text-right">
                <div className="text-xl font-bold text-gray-800">{deck.wins}–{deck.losses}</div>
                <button onClick={enterEdit} className="text-xs text-blue-500 hover:text-blue-700">Edit</button>
              </div>
            </div>

            {/* AI description */}
            {deck.ai_description && (
              <div className="bg-purple-50 border border-purple-100 rounded p-3">
                <div className="text-xs font-semibold text-purple-600 mb-1">✨ AI Analysis</div>
                <p className="text-xs text-gray-700 leading-relaxed">{deck.ai_description}</p>
              </div>
            )}

            {/* Read-only card lists */}
            {viewDeckIds.length > 0 && (
              <details>
                <summary className="text-sm font-medium text-gray-700 cursor-pointer select-none">
                  🃏 Deck ({viewDeckIds.length} cards)
                </summary>
                <div className="mt-2 columns-2 gap-2 text-xs text-gray-600 max-h-48 overflow-y-auto">
                  {viewDeckIds.map((id) => (
                    <div key={id} className="leading-5">{cardMap.get(id) ?? `#${id}`}</div>
                  ))}
                </div>
              </details>
            )}
            {viewPoolIds.length > 0 && (
              <details>
                <summary className="text-sm font-medium text-gray-700 cursor-pointer select-none">
                  🎴 Full Pool ({viewPoolIds.length} cards)
                </summary>
                <div className="mt-2 columns-2 gap-2 text-xs text-gray-500 max-h-48 overflow-y-auto">
                  {viewPoolIds.map((id) => (
                    <div key={id} className="leading-5">{cardMap.get(id) ?? `#${id}`}</div>
                  ))}
                </div>
              </details>
            )}
            {viewSideIds.length > 0 && (
              <details>
                <summary className="text-sm font-medium text-gray-700 cursor-pointer select-none">
                  📋 Sideboard ({viewSideIds.length} cards)
                </summary>
                <div className="mt-2 columns-2 gap-2 text-xs text-gray-500 max-h-48 overflow-y-auto">
                  {viewSideIds.map((id) => (
                    <div key={id} className="leading-5">{cardMap.get(id) ?? `#${id}`}</div>
                  ))}
                </div>
              </details>
            )}
            {viewDeckIds.length === 0 && viewPoolIds.length === 0 && (
              <p className="text-xs text-gray-400 italic">No cards recorded yet — upload photos to analyse, or click Edit to add manually.</p>
            )}
          </>
        )}
      </div>

      {/* ── footer actions ─────────────────────────────────────────────────── */}
      <div className="border-t border-gray-100 px-4 py-2 flex items-center justify-between bg-gray-50">
        <button
          onClick={() => aiMutation.mutate()}
          disabled={aiMutation.isPending}
          className="text-xs bg-purple-100 text-purple-700 px-3 py-1 rounded hover:bg-purple-200 disabled:opacity-50"
        >
          {aiMutation.isPending ? 'Generating…' : '✨ Generate AI Description'}
        </button>
        <button
          onClick={() => { if (window.confirm('Delete this deck?')) deleteMutation.mutate() }}
          className="text-xs text-red-400 hover:text-red-600"
        >Delete</button>
      </div>

      {/* ── player's own feedback ─────────────────────────────────────────── */}
      {isMyDeck && userId && !fbSubmitted && (
        <div className="border-t border-purple-200 bg-purple-50 p-4 space-y-3">
          <div className="font-medium text-sm text-purple-800">✨ Your Post-Draft Feedback</div>
          <p className="text-xs text-purple-600">Share your thoughts — helps the cube owner improve.</p>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Overall Rating (1–10)</label>
            <input
              type="number" min={1} max={10}
              value={fbRating}
              onChange={(e) => setFbRating(e.target.value === '' ? '' : parseInt(e.target.value))}
              className="w-32 px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Overall thoughts</label>
            <textarea rows={2} value={fbThoughts} onChange={(e) => setFbThoughts(e.target.value)}
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
              placeholder="How was the draft experience?" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Standout cards (comma-separated names)</label>
            <input value={fbStandout} onChange={(e) => setFbStandout(e.target.value)}
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
              placeholder="e.g. Recurring Nightmare, The One Ring" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Underperforming cards</label>
            <input value={fbUnderperformer} onChange={(e) => setFbUnderperformer(e.target.value)}
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
              placeholder="Cards that felt weak or unplayable" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Cards you'd recommend adding to the cube</label>
            <input value={fbCardsToAdd} onChange={(e) => setFbCardsToAdd(e.target.value)}
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
              placeholder="e.g. Mana Drain, Snapcaster Mage" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Cards you'd recommend cutting from the cube</label>
            <input value={fbCardsToCut} onChange={(e) => setFbCardsToCut(e.target.value)}
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
              placeholder="e.g. Armageddon, Stasis" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Recommendations for the cube owner</label>
            <textarea rows={2} value={fbRecs} onChange={(e) => setFbRecs(e.target.value)}
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
              placeholder="What would you add, cut, or change?" />
          </div>
          <button
            onClick={() => fbMutation.mutate()}
            disabled={fbMutation.isPending}
            className="bg-purple-600 text-white px-4 py-2 rounded text-sm hover:bg-purple-700 disabled:opacity-50"
          >{fbMutation.isPending ? 'Submitting…' : 'Submit Feedback'}</button>
        </div>
      )}
      {isMyDeck && fbSubmitted && (
        <div className="border-t border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          ✅ Thanks for your feedback!
        </div>
      )}

      {/* ── owner entry for this player ───────────────────────────────────── */}
      {isCubeOwner && !isMyDeck && (
        <div className="border-t border-amber-200 bg-amber-50 p-4">
          <button
            onClick={() => setShowOwnerFbForm((v) => !v)}
            className="font-medium text-sm text-amber-800 hover:text-amber-900 flex items-center gap-2"
          >
            📋 Enter Feedback for {deck.player_name ?? 'Player'}
            <span className="text-xs text-gray-400">{showOwnerFbForm ? '▲' : '▼'}</span>
          </button>
          {showOwnerFbForm && !ownerFbSaved && (
            <div className="mt-3 space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Overall Rating (1–10)</label>
                <input
                  type="number" min={1} max={10}
                  value={ownerFbRating}
                  onChange={(e) => setOwnerFbRating(e.target.value === '' ? '' : parseInt(e.target.value))}
                  className="w-32 px-3 py-1.5 border border-gray-300 rounded text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Overall thoughts</label>
                <textarea rows={2} value={ownerFbThoughts} onChange={(e) => setOwnerFbThoughts(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                  placeholder="How was the draft experience for this player?" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Standout cards (comma-separated names)</label>
                <input value={ownerFbStandout} onChange={(e) => setOwnerFbStandout(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                  placeholder="e.g. Recurring Nightmare, The One Ring" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Underperforming cards</label>
                <input value={ownerFbUnderperformer} onChange={(e) => setOwnerFbUnderperformer(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                  placeholder="Cards that felt weak or unplayable" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Cards to recommend adding to the cube</label>
                <input value={ownerFbCardsToAdd} onChange={(e) => setOwnerFbCardsToAdd(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                  placeholder="e.g. Mana Drain, Snapcaster Mage" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Cards to recommend cutting from the cube</label>
                <input value={ownerFbCardsToCut} onChange={(e) => setOwnerFbCardsToCut(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                  placeholder="e.g. Armageddon, Stasis" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Recommendations for the cube owner</label>
                <textarea rows={2} value={ownerFbRecs} onChange={(e) => setOwnerFbRecs(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                  placeholder="What would they add, cut, or change?" />
              </div>
              <button
                onClick={() => ownerFbMutation.mutate()}
                disabled={ownerFbMutation.isPending}
                className="bg-amber-600 text-white px-4 py-2 rounded text-sm hover:bg-amber-700 disabled:opacity-50"
              >{ownerFbMutation.isPending ? 'Saving…' : 'Save Feedback'}</button>
            </div>
          )}
          {ownerFbSaved && (
            <p className="mt-2 text-sm text-green-700">✅ Feedback saved for {deck.player_name ?? 'Player'}.</p>
          )}
        </div>
      )}
    </div>
  )
}

// ── HostedEventView ───────────────────────────────────────────────────────────

function HostedEventView({
  draftId,
  draft,
  cube,
  userId,
  isCubeOwner,
  cardMap,
  cubeCards,
}: {
  draftId: number
  draft: NonNullable<ReturnType<typeof Object.create>>
  cube: ReturnType<typeof Object.create> | undefined
  userId?: number
  isCubeOwner: boolean
  cardMap: Map<number, string>
  cubeCards: CubeCard[]
}) {
  const queryClient = useQueryClient()
  const status: string = draft.status ?? 'active'

  const { data: seats = [] } = useQuery<DraftSeat[]>({
    queryKey: ['seating', draftId],
    queryFn: () => draftsApi.getSeating(draftId),
    enabled: ['seating_assigned', 'drafting', 'deck_submission', 'in_rounds', 'completed'].includes(status),
  })

  const { data: rounds = [] } = useQuery<DraftRound[]>({
    queryKey: ['rounds', draftId],
    queryFn: () => draftsApi.getAllRounds(draftId),
    enabled: ['in_rounds', 'completed'].includes(status),
    refetchInterval: status === 'in_rounds' ? 15000 : false,
  })

  const startMutation = useMutation({
    mutationFn: () => draftsApi.startEvent(draftId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['draft', draftId] })
      queryClient.invalidateQueries({ queryKey: ['seating', draftId] })
    },
  })

  const advanceMutation = useMutation({
    mutationFn: () => draftsApi.advanceStatus(draftId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['draft', draftId] }),
  })

  const nextRoundMutation = useMutation({
    mutationFn: () => draftsApi.startNextRound(draftId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['draft', draftId] })
      queryClient.invalidateQueries({ queryKey: ['rounds', draftId] })
    },
  })

  const decks = draft.user_decks ?? []
  const currentRound = rounds.find((r: DraftRound) => r.round_number === draft.current_round)
  const allDecksSubmitted = decks.length > 0 && (draft.num_players ? decks.length >= draft.num_players : true)

  // ── Phase: active ────────────────────────────────────────────────────────
  if (status === 'active') {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 space-y-4">
        <h2 className="font-semibold text-lg text-amber-800">⏳ Waiting to Start</h2>
        <p className="text-sm text-amber-700">
          {(draft.participants ?? []).length} / {draft.num_players ?? '?'} players joined.
          Once everyone is in, the host can assign seats and start the event.
        </p>
        {isCubeOwner && (
          <button
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending}
            className="bg-amber-600 text-white px-5 py-2 rounded-md hover:bg-amber-700 text-sm disabled:opacity-50"
          >
            {startMutation.isPending ? 'Assigning seats…' : '🎲 Assign Seats & Start'}
          </button>
        )}
        {startMutation.isError && (
          <p className="text-sm text-red-600">Error starting event. Try again.</p>
        )}
      </div>
    )
  }

  // ── Phase: seating_assigned ──────────────────────────────────────────────
  if (status === 'seating_assigned') {
    return (
      <div className="space-y-4">
        <div className="bg-white rounded-lg shadow-md p-5">
          <h2 className="font-semibold text-lg mb-3">🪑 Seating Chart</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[...seats].sort((a, b) => a.seat_number - b.seat_number).map((s: DraftSeat) => (
              <div key={s.user_id} className={`text-center p-3 rounded-lg border-2 ${s.user_id === userId ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                <div className="text-2xl font-bold text-gray-600">#{s.seat_number}</div>
                <div className="text-sm font-medium mt-1">{s.username}</div>
                {s.user_id === userId && <div className="text-xs text-blue-600 mt-0.5">← You</div>}
              </div>
            ))}
          </div>
        </div>

        {/* Cube settings info */}
        {cube && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm">
            <div className="font-semibold text-gray-700 mb-2">📋 Draft Info</div>
            <div className="flex flex-wrap gap-6 text-gray-600">
              <span>❤️ Starting life: <strong>{cube.life_total ?? 20}</strong></span>
              <span>📦 Packs: <strong>{cube.pack_count ?? 3}</strong> × {cube.pack_size ?? 15} cards</span>
              {draft.num_rounds && <span>🏆 Rounds: <strong>{draft.num_rounds}</strong> (BO{draft.best_of ?? 1})</span>}
            </div>
            {cube.draft_rules && <p className="mt-2 text-gray-600"><strong>Draft rules:</strong> {cube.draft_rules}</p>}
            {cube.gameplay_rules && <p className="mt-1 text-gray-600"><strong>Gameplay rules:</strong> {cube.gameplay_rules}</p>}
          </div>
        )}

        {isCubeOwner && (
          <button
            onClick={() => advanceMutation.mutate()}
            disabled={advanceMutation.isPending}
            className="bg-blue-600 text-white px-5 py-2 rounded-md hover:bg-blue-700 text-sm disabled:opacity-50"
          >
            {advanceMutation.isPending ? 'Advancing…' : '▶️ Advance to Drafting Phase'}
          </button>
        )}
      </div>
    )
  }

  // ── Phase: drafting ──────────────────────────────────────────────────────
  if (status === 'drafting') {
    return (
      <div className="space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-5">
          <h2 className="font-semibold text-lg text-blue-800 mb-2">🃏 Drafting in Progress</h2>
          {cube && (
            <div className="text-sm text-blue-700 flex flex-wrap gap-4 mb-3">
              <span>📦 {cube.pack_count ?? 3} packs of {cube.pack_size ?? 15} cards</span>
              {draft.num_rounds && <span>🏆 {draft.num_rounds} rounds (BO{draft.best_of ?? 1})</span>}
            </div>
          )}
          {cube?.draft_rules && <p className="text-sm text-blue-700"><strong>Rules:</strong> {cube.draft_rules}</p>}
          {cube?.gameplay_rules && <p className="text-sm text-blue-700 mt-1"><strong>Gameplay:</strong> {cube.gameplay_rules}</p>}
        </div>

        {isCubeOwner && (
          <button
            onClick={() => advanceMutation.mutate()}
            disabled={advanceMutation.isPending}
            className="bg-indigo-600 text-white px-5 py-2 rounded-md hover:bg-indigo-700 text-sm disabled:opacity-50"
          >
            {advanceMutation.isPending ? 'Advancing…' : '▶️ Advance to Deck Submission'}
          </button>
        )}
      </div>
    )
  }

  // ── Phase: deck_submission ───────────────────────────────────────────────
  if (status === 'deck_submission') {
    const myDeck = userId ? decks.find((d: {user_id: number}) => d.user_id === userId) : undefined
    return (
      <div className="space-y-4">
        {/* Submission progress (owner view) */}
        {isCubeOwner && (
          <div className="bg-white rounded-lg shadow-md p-4">
            <h2 className="font-semibold mb-2">📋 Deck Submission Progress</h2>
            <div className="flex flex-wrap gap-2 text-sm">
              {(draft.participants ?? []).map((p: {user_id:number; username:string}) => {
                const submitted = decks.some((d: {user_id:number}) => d.user_id === p.user_id)
                return (
                  <span key={p.user_id} className={`px-3 py-1 rounded-full border text-xs font-medium ${
                    submitted ? 'bg-green-100 border-green-300 text-green-700' : 'bg-gray-100 border-gray-300 text-gray-500'
                  }`}>
                    {submitted ? '✓ ' : '⏳ '}{p.username}
                  </span>
                )
              })}
            </div>
            <div className="mt-4 flex items-center gap-3">
              <span className="text-sm text-gray-600">{decks.length}/{draft.num_players ?? '?'} submitted</span>
              <button
                onClick={() => nextRoundMutation.mutate()}
                disabled={!allDecksSubmitted || nextRoundMutation.isPending}
                className="bg-green-600 text-white px-4 py-2 rounded-md text-sm hover:bg-green-700 disabled:opacity-50"
              >
                {nextRoundMutation.isPending ? 'Generating pairings…' : '🏁 Start Round 1'}
              </button>
              {!allDecksSubmitted && (
                <span className="text-xs text-yellow-600">Waiting for all players to submit</span>
              )}
            </div>
          </div>
        )}

        {/* My Deck submission */}
        <div className="bg-white rounded-lg shadow-md border-2 border-indigo-200 overflow-hidden">
          <div className="bg-indigo-600 text-white px-5 py-3 font-semibold">
            {myDeck ? `✅ Your Deck — Submitted` : `📤 Submit Your Deck`}
          </div>
          {myDeck ? (
            <DeckCard
              deck={myDeck}
              draftId={draftId}
              cardMap={cardMap}
              onUpdated={() => queryClient.invalidateQueries({ queryKey: ['draft', draftId] })}
              userId={userId}
              isCubeOwner={isCubeOwner}
              isMyDeck={true}
            />
          ) : (
            <div className="p-5">
              <AddDeckForm
                draftId={draftId}
                cubeCards={cubeCards}
                userId={userId}
                defaultPlayerName={(draft.participants ?? []).find((p: {user_id:number; username:string}) => p.user_id === userId)?.username}
                onCreated={() => queryClient.invalidateQueries({ queryKey: ['draft', draftId] })}
              />
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Phase: in_rounds ────────────────────────────────────────────────────
  if (status === 'in_rounds') {
    return (
      <div className="space-y-4">
        {/* Standings banner */}
        <div className="bg-white rounded-lg shadow-md p-4">
          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
            <h2 className="font-semibold text-lg">
              Round {draft.current_round} / {draft.num_rounds ?? '?'}
            </h2>
            {isCubeOwner && (
              <div className="flex gap-2 flex-wrap items-center">
                {currentRound?.status === 'complete' && (draft.current_round ?? 0) >= (draft.num_rounds ?? 0) ? (
                  // All rounds done — primary end button
                  <button
                    onClick={() => advanceMutation.mutate()}
                    disabled={advanceMutation.isPending}
                    className="bg-green-600 text-white px-4 py-1.5 rounded-md text-sm hover:bg-green-700 disabled:opacity-50"
                  >
                    {advanceMutation.isPending ? '…' : '🏁 End Event'}
                  </button>
                ) : currentRound?.status === 'complete' ? (
                  // Round done but more rounds remain — next round + early-end
                  <>
                    <button
                      onClick={() => nextRoundMutation.mutate()}
                      disabled={nextRoundMutation.isPending}
                      className="bg-blue-600 text-white px-4 py-1.5 rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
                    >
                      {nextRoundMutation.isPending ? '…' : `▶️ Start Round ${(draft.current_round ?? 0) + 1}`}
                    </button>
                    <button
                      onClick={() => {
                        if (window.confirm('End the event early after this round? Final standings will be recorded.')) {
                          advanceMutation.mutate()
                        }
                      }}
                      disabled={advanceMutation.isPending}
                      className="border border-red-300 text-red-600 px-4 py-1.5 rounded-md text-sm hover:bg-red-50 disabled:opacity-50"
                    >
                      {advanceMutation.isPending ? '…' : 'End Early'}
                    </button>
                  </>
                ) : (
                  // Round still in progress — only early-end available
                  <button
                    onClick={() => {
                      if (window.confirm('End the event early? The current round is still in progress. Final standings will be recorded now.')) {
                        advanceMutation.mutate()
                      }
                    }}
                    disabled={advanceMutation.isPending}
                    className="border border-red-300 text-red-600 px-4 py-1.5 rounded-md text-sm hover:bg-red-50 disabled:opacity-50"
                  >
                    {advanceMutation.isPending ? '…' : '🛑 End Early'}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Standings table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-200 text-left text-gray-500 text-xs uppercase">
                <th className="py-1 pr-3">#</th><th className="py-1 pr-3">Player</th>
                <th className="py-1 pr-3 text-center">W</th><th className="py-1 text-center">L</th>
              </tr></thead>
              <tbody>
                {[...decks].sort((a: {wins:number}, b: {wins:number}) => b.wins - a.wins).map((d: {id:number; player_name?:string; wins:number; losses:number; user_id:number}, i: number) => (
                  <tr key={d.id} className="border-b border-gray-100 text-sm">
                    <td className="py-1 pr-3 text-gray-400">{i + 1}</td>
                    <td className={`py-1 pr-3 ${d.user_id === userId ? 'font-semibold text-indigo-700' : ''}`}>
                      {d.player_name ?? '—'}{d.user_id === userId ? ' (you)' : ''}
                    </td>
                    <td className="py-1 pr-3 text-center text-green-700">{d.wins}</td>
                    <td className="py-1 text-center text-red-600">{d.losses}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pairings for current round */}
        {currentRound && (
          <div className="space-y-3">
            <h3 className="font-semibold text-gray-700">Round {currentRound.round_number} Pairings</h3>
            {currentRound.pairings.map((pairing: DraftPairing) => (
              <PairingCard
                key={pairing.id}
                pairing={pairing}
                draftId={draftId}
                userId={userId}
                onUpdated={() => queryClient.invalidateQueries({ queryKey: ['rounds', draftId] })}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Phase: completed ─────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      {/* All player deck cards — includes per-slot feedback */}
      {(decks as UserDeck[]).length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {(decks as UserDeck[]).map((d) => (
            <div key={d.id} className={`rounded-lg shadow-md overflow-hidden ${d.user_id === userId ? 'border-2 border-indigo-200' : ''}`}>
              <div className={`px-5 py-3 flex items-center justify-between ${d.user_id === userId ? 'bg-indigo-600 text-white' : 'bg-gray-50 border-b'}`}>
                <div className={`font-medium ${d.user_id === userId ? 'text-white' : 'text-gray-800'}`}>
                  {d.user_id === userId ? '🧑‍💻 ' : '👤 '}{d.player_name ?? 'Player'}
                </div>
                <div className={`text-sm ${d.user_id === userId ? 'text-indigo-200' : 'text-gray-500'}`}>{d.wins}–{d.losses}</div>
              </div>
              <DeckCard
                deck={d}
                draftId={draftId}
                cardMap={cardMap}
                onUpdated={() => queryClient.invalidateQueries({ queryKey: ['draft', draftId] })}
                userId={userId}
                isCubeOwner={isCubeOwner}
                isMyDeck={d.user_id === userId}
              />
            </div>
          ))}
        </div>
      )}
      <PostDraftSection
        draftId={draftId}
        userId={userId}
        isCubeOwner={isCubeOwner}
        draft={draft}
        rounds={rounds}
        cardMap={cardMap}
      />
    </div>
  )
}

// ── PairingCard ───────────────────────────────────────────────────────────────

function LifeTracker({ label, startingLife }: { label: string; startingLife: number }) {
  const [life, setLife] = useState(startingLife)
  const adjust = (n: number) => setLife((l) => Math.max(0, l + n))
  return (
    <div className="text-center">
      <div className="text-xs text-gray-500 mb-1 truncate max-w-[110px]">{label}</div>
      <div className={`text-4xl font-bold tabular-nums ${life <= 5 ? 'text-red-600' : life <= 10 ? 'text-yellow-600' : 'text-gray-900'}`}>
        {life}
      </div>
      <div className="flex gap-1 mt-2 justify-center">
        {[-5,-1].map((n) => (
          <button key={n} onClick={() => adjust(n)} className="w-8 h-8 rounded bg-red-100 text-red-700 hover:bg-red-200 text-sm font-bold">{n}</button>
        ))}
        {[1,5].map((n) => (
          <button key={n} onClick={() => adjust(n)} className="w-8 h-8 rounded bg-green-100 text-green-700 hover:bg-green-200 text-sm font-bold">+{n}</button>
        ))}
      </div>
      <button onClick={() => setLife(startingLife)} className="mt-1 text-xs text-gray-400 hover:text-gray-600">Reset</button>
    </div>
  )
}

function PairingCard({
  pairing,
  draftId,
  userId,
  onUpdated,
}: {
  pairing: DraftPairing
  draftId: number
  userId?: number
  onUpdated: () => void
}) {
  const [myWins, setMyWins] = useState(0)
  const [oppWins, setOppWins] = useState(0)
  const [showFeedback, setShowFeedback] = useState(false)
  const [fbGeneral, setFbGeneral] = useState('')
  const [fbLikedNotes, setFbLikedNotes] = useState('')
  const [fbDislikedNotes, setFbDislikedNotes] = useState('')

  const [conflictMsg, setConflictMsg] = useState<string | null>(null)

  const isBye = !pairing.player2_user_id
  const isMyPairing = pairing.player1_user_id === userId || pairing.player2_user_id === userId
  const imPlayer1 = pairing.player1_user_id === userId

  const resultMutation = useMutation({
    mutationFn: () => draftsApi.submitMatchResult(draftId, pairing.id, {
      player1_wins: imPlayer1 ? myWins : oppWins,
      player2_wins: imPlayer1 ? oppWins : myWins,
    }, userId),
    onSuccess: () => { setConflictMsg(null); onUpdated() },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 409 && detail) {
        setConflictMsg(detail)
      }
    },
  })

  const feedbackMutation = useMutation({
    mutationFn: () => draftsApi.submitRoundFeedback(draftId, pairing.id, {
      liked_notes: fbLikedNotes || undefined,
      disliked_notes: fbDislikedNotes || undefined,
      general_thoughts: fbGeneral || undefined,
    }, userId),
    onSuccess: () => setShowFeedback(false),
  })

  const myConfirmed = imPlayer1 ? pairing.player1_confirmed : pairing.player2_confirmed
  const oppConfirmed = imPlayer1 ? pairing.player2_confirmed : pairing.player1_confirmed

  return (
    <div className={`bg-white rounded-lg shadow border ${pairing.status === 'complete' ? 'border-green-300' : 'border-gray-200'} overflow-hidden`}>
      {/* Header */}
      <div className={`px-4 py-2 flex items-center justify-between text-sm ${pairing.status === 'complete' ? 'bg-green-50' : 'bg-gray-50'}`}>
        <span className="font-medium">
          {pairing.player1_name ?? 'TBD'} vs {isBye ? '🌟 BYE' : (pairing.player2_name ?? 'TBD')}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          pairing.status === 'complete' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
        }`}>
          {pairing.status === 'complete' ? '✓ Complete' : isBye ? '🌟 Bye' : 'In progress'}
        </span>
      </div>

      {pairing.status === 'complete' && (
        <div className="px-4 py-3 text-sm text-gray-600">
          Final: {pairing.player1_name} {pairing.player1_wins} – {pairing.player2_wins} {pairing.player2_name}
          {pairing.winner_user_id && (
            <span className="ml-2 text-green-700 font-medium">
              🏆 {pairing.winner_user_id === pairing.player1_user_id ? pairing.player1_name : pairing.player2_name} wins
            </span>
          )}
        </div>
      )}

      {/* Life tracker + score entry for my pairing */}
      {isMyPairing && !isBye && pairing.status !== 'complete' && (
        <div className="px-4 py-4 space-y-4">
          {/* Life trackers */}
          <div className="grid grid-cols-2 gap-4 p-3 bg-gray-50 rounded-lg">
            <LifeTracker label={pairing.player1_name ?? 'Player 1'} startingLife={20} />
            <LifeTracker label={pairing.player2_name ?? 'Player 2'} startingLife={20} />
          </div>

          {/* Score entry */}
          <div className="border border-gray-200 rounded-lg p-3">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Submit Result</div>
            <div className="flex items-center gap-3">
              <div className="text-sm text-gray-600">{imPlayer1 ? pairing.player1_name : pairing.player2_name} wins:</div>
              <input
                type="number" min={0} max={3}
                value={myWins}
                onChange={(e) => setMyWins(parseInt(e.target.value) || 0)}
                className="w-16 px-2 py-1 border border-gray-300 rounded text-sm text-center"
              />
              <span className="text-gray-400">–</span>
              <input
                type="number" min={0} max={3}
                value={oppWins}
                onChange={(e) => setOppWins(parseInt(e.target.value) || 0)}
                className="w-16 px-2 py-1 border border-gray-300 rounded text-sm text-center"
              />
              <div className="text-sm text-gray-600">{imPlayer1 ? pairing.player2_name : pairing.player1_name} wins</div>
              <button
                onClick={() => resultMutation.mutate()}
                disabled={resultMutation.isPending}
                className="ml-2 bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {resultMutation.isPending ? '…' : 'Submit'}
              </button>
            </div>
            <div className="mt-2 text-xs text-gray-400 flex gap-3">
              <span className={`px-2 py-0.5 rounded-full ${myConfirmed === 'yes' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                You: {myConfirmed === 'yes' ? '✓ confirmed' : 'not submitted'}
              </span>
              <span className={`px-2 py-0.5 rounded-full ${oppConfirmed === 'yes' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                Opponent: {oppConfirmed === 'yes' ? '✓ confirmed' : 'not submitted'}
              </span>
            </div>
            {conflictMsg && (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                ⚠️ {conflictMsg}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Round feedback toggle */}
      {isMyPairing && !isBye && (
        <div className="border-t border-gray-100 px-4 py-2 flex items-center justify-between">
          <button
            onClick={() => setShowFeedback((v) => !v)}
            className="text-xs text-purple-600 hover:text-purple-800"
          >
            ✨ {showFeedback ? 'Hide' : 'Give'} Round Feedback
          </button>
        </div>
      )}

      {showFeedback && (
        <div className="border-t border-gray-100 bg-purple-50 px-4 py-4 space-y-3">
          <div className="text-sm font-medium text-purple-700">Round Feedback</div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Cards you liked</label>
            <input
              value={fbLikedNotes}
              onChange={(e) => setFbLikedNotes(e.target.value)}
              placeholder="e.g. Lightning Bolt was great"
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Cards you disliked</label>
            <input
              value={fbDislikedNotes}
              onChange={(e) => setFbDislikedNotes(e.target.value)}
              placeholder="e.g. Armageddon felt too strong"
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">General thoughts</label>
            <textarea
              rows={2}
              value={fbGeneral}
              onChange={(e) => setFbGeneral(e.target.value)}
              placeholder="How did the match feel?"
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
          </div>
          <button
            onClick={() => feedbackMutation.mutate()}
            disabled={feedbackMutation.isPending}
            className="bg-purple-600 text-white px-4 py-1.5 rounded text-sm hover:bg-purple-700 disabled:opacity-50"
          >
            {feedbackMutation.isPending ? 'Saving…' : 'Submit Feedback'}
          </button>
        </div>
      )}
    </div>
  )
}

// ── PostDraftSection ──────────────────────────────────────────────────────────

function PostDraftSection({
  draftId,
  isCubeOwner,
  draft,
  rounds,
}: {
  draftId: number
  userId?: number
  isCubeOwner: boolean
  draft: Record<string, unknown>
  rounds: DraftRound[]
  cardMap: Map<number, string>
}) {
  const [showOwnerSummary, setShowOwnerSummary] = useState(false)

  const { data: summary } = useQuery({
    queryKey: ['fullSummary', draftId],
    queryFn: () => draftsApi.getFullSummary(draftId),
    enabled: showOwnerSummary,
  })

  const decks: {id:number; player_name?:string; wins:number; losses:number}[] = (draft.user_decks as never[]) ?? []
  const sorted = [...decks].sort((a, b) => b.wins - a.wins)

  return (
    <div className="space-y-4">
      {/* Final standings */}
      <div className="bg-white rounded-lg shadow-md p-5">
        <h2 className="font-semibold text-xl mb-3">🏆 Final Standings</h2>
        <ol className="space-y-2">
          {sorted.map((d, i) => (
            <li key={d.id} className="flex items-center gap-3 text-sm">
              <span className="text-gray-400 w-5 text-center">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i+1}.`}</span>
              <span className="flex-1 font-medium">{d.player_name ?? `Player ${d.id}`}</span>
              <span className="font-mono text-gray-600">{d.wins}–{d.losses}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* All rounds summary */}
      {rounds.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-5">
          <h2 className="font-semibold mb-3">📋 Round Results</h2>
          <div className="space-y-3">
            {rounds.map((round) => (
              <div key={round.id}>
                <div className="text-sm font-medium text-gray-500 mb-1">Round {round.round_number}</div>
                <div className="space-y-1">
                  {round.pairings.map((p) => (
                    <div key={p.id} className="text-sm text-gray-700 flex gap-2">
                      <span>{p.player1_name ?? '?'}</span>
                      <span className="font-mono text-gray-400">{p.player1_wins}–{p.player2_wins}</span>
                      <span>{p.player2_name ?? '?'}</span>
                      {p.winner_user_id === p.player1_user_id && <span className="text-green-600">← 🏆</span>}
                      {p.winner_user_id === p.player2_user_id && <span className="text-green-600">🏆 →</span>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Owner full summary */}
      {isCubeOwner && (
        <div className="bg-white rounded-lg shadow-md p-5">
          <button
            onClick={() => setShowOwnerSummary((v) => !v)}
            className="font-semibold text-blue-700 hover:text-blue-900 flex items-center gap-2"
          >
            📊 Full Event Summary (Owner View)
            <span className="text-sm text-gray-400">{showOwnerSummary ? '▲' : '▼'}</span>
          </button>

          {showOwnerSummary && summary && (
            <div className="mt-4 space-y-4">
              {/* Card feedback tally */}
              {(summary as {card_mentions?: {name:string; liked:number; disliked:number}[]}).card_mentions && (
                <div>
                  <div className="font-medium text-sm text-gray-600 mb-2">💬 Card Feedback Tally</div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead><tr className="border-b text-gray-500">
                        <th className="text-left py-1 pr-4">Card</th>
                        <th className="text-center py-1 pr-4 text-green-600">👍 Liked</th>
                        <th className="text-center py-1 text-red-600">👎 Disliked</th>
                      </tr></thead>
                      <tbody>
                        {((summary as {card_mentions: {name:string; liked:number; disliked:number}[]}).card_mentions ?? []).map((c) => (
                          <tr key={c.name} className="border-b border-gray-100">
                            <td className="py-1 pr-4">{c.name}</td>
                            <td className="text-center py-1 pr-4 text-green-700">{c.liked}</td>
                            <td className="text-center py-1 text-red-600">{c.disliked}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              {/* Player feedback */}
              {(summary as {post_draft_feedback?: {username:string; rating:number; thoughts:string; recs:string}[]}).post_draft_feedback && (
                <div>
                  <div className="font-medium text-sm text-gray-600 mb-2">🗣️ Player Feedback</div>
                  <div className="space-y-2">
                    {((summary as {post_draft_feedback:{username:string; overall_rating:number; overall_thoughts:string; recommendations_for_owner:string}[]}).post_draft_feedback ?? []).map((fb, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg p-3 text-sm">
                        <div className="font-medium">{fb.username} — {fb.overall_rating}/10</div>
                        {fb.overall_thoughts && <p className="text-gray-600 mt-1">{fb.overall_thoughts}</p>}
                        {fb.recommendations_for_owner && <p className="text-gray-500 mt-1 italic">Rec: {fb.recommendations_for_owner}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          {showOwnerSummary && !summary && (
            <p className="mt-3 text-sm text-gray-500">Loading summary…</p>
          )}
        </div>
      )}
    </div>
  )
}
