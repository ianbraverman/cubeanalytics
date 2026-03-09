import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { draftsApi, type UserDraftSummary } from '../../api/drafts'
import Layout from '../../components/Layout'
import { useAuth } from '../../auth/AuthProvider'

export default function MyDraftsPage() {
  const { user } = useAuth()

  const { data: drafts = [], isLoading } = useQuery({
    queryKey: ['myDrafts', user?.id],
    queryFn: () => draftsApi.getDraftsForUser(user!.id),
    enabled: !!user,
  })

  const active = drafts.filter(
    (d) => d.status !== 'completed' && d.status !== undefined,
  )
  const completed = drafts.filter((d) => d.status === 'completed')

  // Overall stats across all drafts where user had a deck
  const decksWithRecord = drafts.filter((d) => d.my_deck)
  const totalWins = decksWithRecord.reduce((n, d) => n + (d.my_deck?.wins ?? 0), 0)
  const totalLosses = decksWithRecord.reduce((n, d) => n + (d.my_deck?.losses ?? 0), 0)
  const bestRecord = decksWithRecord.reduce<UserDraftSummary | null>((best, d) => {
    if (!d.my_deck) return best
    if (!best?.my_deck) return d
    return d.my_deck.wins > (best.my_deck?.wins ?? 0) ? d : best
  }, null)

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6 py-2">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-2xl font-bold text-gray-900">My Drafts</h1>
          <Link
            to="/join-draft"
            className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm hover:bg-indigo-700"
          >
            + Join a Draft
          </Link>
        </div>

        {/* Stats bar */}
        {decksWithRecord.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Drafts', value: drafts.length },
              { label: 'Decks submitted', value: decksWithRecord.length },
              { label: 'Overall record', value: `${totalWins}–${totalLosses}` },
              {
                label: 'Best performance',
                value: bestRecord?.my_deck
                  ? `${bestRecord.my_deck.wins}–${bestRecord.my_deck.losses}`
                  : '—',
              },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-lg shadow-sm border border-gray-100 p-4 text-center">
                <div className="text-2xl font-bold text-indigo-700">{s.value}</div>
                <div className="text-xs text-gray-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {isLoading && (
          <p className="text-gray-500 text-sm">Loading your drafts…</p>
        )}

        {/* ── Active / In-progress drafts ── */}
        {active.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block animate-pulse" />
              Active Drafts
            </h2>
            <div className="space-y-3">
              {active.map((d) => (
                <DraftRow key={d.id} draft={d} isActive />
              ))}
            </div>
          </section>
        )}

        {/* ── Completed drafts ── */}
        {completed.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Past Drafts</h2>
            <div className="space-y-3">
              {completed.map((d) => (
                <DraftRow key={d.id} draft={d} isActive={false} />
              ))}
            </div>
          </section>
        )}

        {!isLoading && drafts.length === 0 && (
          <div className="text-center py-20 text-gray-400">
            <p className="text-lg">You haven't joined any drafts yet.</p>
            <p className="text-sm mt-1">
              Use{' '}
              <Link to="/join-draft" className="text-indigo-600 hover:underline">
                Join Draft
              </Link>{' '}
              to enter a draft code and password.
            </p>
          </div>
        )}
      </div>
    </Layout>
  )
}

// ── DraftRow sub-component ────────────────────────────────────────────────────

function statusLabel(status?: string) {
  const map: Record<string, string> = {
    active: 'Waiting to start',
    seating_assigned: 'Seating assigned',
    drafting: 'Drafting',
    deck_submission: 'Deck submission',
    in_rounds: 'Rounds in progress',
    completed: 'Completed',
  }
  return map[status ?? ''] ?? status ?? 'Active'
}

function statusColor(status?: string) {
  if (status === 'completed') return 'bg-gray-100 text-gray-600'
  if (status === 'in_rounds') return 'bg-blue-100 text-blue-700'
  return 'bg-yellow-100 text-yellow-700'
}

function DraftRow({
  draft,
  isActive,
}: {
  draft: UserDraftSummary
  isActive: boolean
}) {
  const dateStr = new Date(draft.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

  const deck = draft.my_deck
  const recordStr = deck?.record ?? (deck ? `${deck.wins}–${deck.losses}` : null)

  return (
    <div
      className={`bg-white rounded-lg border shadow-sm transition-shadow hover:shadow-md ${
        isActive ? 'border-indigo-200' : 'border-gray-100'
      }`}
    >
      <Link
        to={`/cubes/${draft.cube_id}/drafts/${draft.id}`}
        className="block p-5"
      >
        <div className="flex items-start justify-between gap-3 flex-wrap">
          {/* Left: event info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-gray-900 text-base truncate">
                {draft.name ?? `Draft #${draft.id}`}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColor(
                  draft.status,
                )}`}
              >
                {statusLabel(draft.status)}
              </span>
              {draft.event_type === 'hosted' && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">
                  🏆 Hosted
                </span>
              )}
            </div>

            <div className="mt-1 text-sm text-gray-500 flex flex-wrap gap-3">
              {draft.cube_name && (
                <span>
                  📦{' '}
                  <span className="text-gray-700 font-medium">{draft.cube_name}</span>
                </span>
              )}
              <span>{dateStr}</span>
              {draft.event_type === 'hosted' && draft.num_rounds && (
                <span>
                  {draft.num_rounds} rounds · BO{draft.best_of ?? 1}
                </span>
              )}
            </div>

            {/* My deck info */}
            {deck ? (
              <div className="mt-2 inline-flex items-center gap-3 bg-indigo-50 border border-indigo-100 rounded-md px-3 py-1.5 text-sm">
                <span className="text-gray-700">
                  {deck.deck_name ? (
                    <>
                      <span className="font-medium">{deck.deck_name}</span>
                      {deck.player_name && (
                        <span className="text-gray-400"> · {deck.player_name}</span>
                      )}
                    </>
                  ) : (
                    <span className="italic text-gray-400">Deck submitted</span>
                  )}
                </span>
                {recordStr && (
                  <span
                    className={`font-mono font-semibold ${
                      deck.wins > deck.losses
                        ? 'text-green-700'
                        : deck.wins < deck.losses
                        ? 'text-red-600'
                        : 'text-gray-600'
                    }`}
                  >
                    {recordStr}
                  </span>
                )}
              </div>
            ) : (
              isActive && (
                <div className="mt-2 text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded px-2 py-1 inline-block">
                  ⏳ No deck submitted yet
                </div>
              )
            )}

            {deck?.ai_description && (
              <p className="mt-2 text-xs text-gray-500 italic line-clamp-2">
                "{deck.ai_description}"
              </p>
            )}
          </div>

          {/* Right: action */}
          <div className="shrink-0 flex flex-col items-end gap-2">
            {isActive ? (
              <span className="bg-indigo-600 text-white text-sm px-4 py-2 rounded-md hover:bg-indigo-700 transition-colors">
                Rejoin →
              </span>
            ) : (
              <span className="text-blue-600 text-sm">View →</span>
            )}
          </div>
        </div>
      </Link>
    </div>
  )
}
