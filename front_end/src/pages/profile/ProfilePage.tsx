import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../../auth/AuthProvider'
import { statisticsApi, PlayerStats, PlayerCardStat } from '../../api/statistics'
import Layout from '../../components/Layout'

// ── Small helpers ────────────────────────────────────────────────────────────

function pct(rate: number | null | undefined): string {
  if (rate == null) return '—'
  return `${(rate * 100).toFixed(1)}%`
}

function record(wins: number, losses: number): string {
  return `${wins}–${losses}`
}

const MTG_COLORS: Record<string, string> = {
  W: '#f9fafb',
  U: '#93c5fd',
  B: '#374151',
  R: '#f87171',
  G: '#4ade80',
}

function ColorPips({ identity }: { identity: string | null }) {
  if (!identity) return <span className="text-gray-400">—</span>
  return (
    <span className="inline-flex gap-0.5">
      {identity.split('').map((c) => (
        <span
          key={c}
          title={c}
          className="inline-block w-4 h-4 rounded-full border border-gray-300 text-xs leading-4 text-center font-bold"
          style={{ backgroundColor: MTG_COLORS[c] ?? '#e5e7eb', color: c === 'W' ? '#374151' : '#fff' }}
        >
          {c}
        </span>
      ))}
    </span>
  )
}

// ── Sub-sections ─────────────────────────────────────────────────────────────

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  )
}

function CubesPlayedSection({ data }: { data: PlayerStats['cubes_played'] }) {
  if (!data.length) return null
  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Cubes Played</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
          <thead className="bg-gray-50 text-gray-600 text-left">
            <tr>
              <th className="px-4 py-2">Cube</th>
              <th className="px-4 py-2 text-right">Drafts</th>
              <th className="px-4 py-2 text-right">Record</th>
              <th className="px-4 py-2 text-right">Win Rate</th>
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <tr key={c.cube_id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-blue-700">
                  <Link to={`/cubes/${c.cube_id}`}>{c.cube_name}</Link>
                </td>
                <td className="px-4 py-2 text-right">{c.draft_count}</td>
                <td className="px-4 py-2 text-right">{record(c.total_wins, c.total_losses)}</td>
                <td className="px-4 py-2 text-right font-semibold">{pct(c.win_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function BreakdownBars({
  title,
  rows,
}: {
  title: string
  rows: { label: string; count: number; wins: number; losses: number; win_rate: number | null }[]
}) {
  if (!rows.length) return null
  const maxCount = Math.max(...rows.map((r) => r.count))
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="font-semibold text-gray-700 mb-3">{title}</h3>
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.label}>
            <div className="flex justify-between text-xs text-gray-600 mb-0.5">
              <span className="capitalize font-medium">{r.label || 'Other'}</span>
              <span>
                {record(r.wins, r.losses)} &nbsp;
                <span className="font-semibold text-gray-800">{pct(r.win_rate)}</span>
              </span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-400 rounded-full"
                style={{ width: `${maxCount ? (r.count / maxCount) * 100 : 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CardTable({
  cards,
  title,
  metric: _metric,
}: {
  cards: PlayerCardStat[]
  title: string
  metric: 'times_played' | 'win_rate'
}) {
  if (!cards.length) return null
  return (
    <div>
      <h3 className="font-semibold text-gray-700 mb-2">{title}</h3>
      <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
        <thead className="bg-gray-50 text-gray-600 text-left">
          <tr>
            <th className="px-3 py-2">Card</th>
            <th className="px-3 py-2 text-right">Drafted</th>
            <th className="px-3 py-2 text-right">Record</th>
            <th className="px-3 py-2 text-right">Win %</th>
          </tr>
        </thead>
        <tbody>
          {cards.map((c) => (
            <tr key={c.card_id} className="border-t border-gray-100 hover:bg-gray-50">
              <td className="px-3 py-2 font-medium text-blue-700">
                <Link to={`/cards/${c.card_id}`}>{c.card_name}</Link>
              </td>
              <td className="px-3 py-2 text-right">{c.times_played}</td>
              <td className="px-3 py-2 text-right">{record(c.wins_with, c.losses_with)}</td>
              <td className="px-3 py-2 text-right font-semibold">{pct(c.win_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function HeadToHeadSection({ data }: { data: PlayerStats['head_to_head'] }) {
  if (!data.length) return null
  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Head-to-Head</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
          <thead className="bg-gray-50 text-gray-600 text-left">
            <tr>
              <th className="px-4 py-2">Opponent</th>
              <th className="px-4 py-2 text-right">Matches</th>
              <th className="px-4 py-2 text-right">Record</th>
              <th className="px-4 py-2 text-right">Win Rate</th>
            </tr>
          </thead>
          <tbody>
            {data.map((h) => (
              <tr key={h.opponent_user_id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-blue-700">
                  <Link to={`/players/${h.opponent_user_id}`}>{h.opponent_username}</Link>
                </td>
                <td className="px-4 py-2 text-right">{h.matches}</td>
                <td className="px-4 py-2 text-right">{record(h.wins, h.losses)}</td>
                <td
                  className={`px-4 py-2 text-right font-semibold ${
                    h.win_rate != null && h.win_rate >= 0.5 ? 'text-green-600' : 'text-red-500'
                  }`}
                >
                  {pct(h.win_rate)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function RecentDraftsSection({ data }: { data: PlayerStats['recent_drafts'] }) {
  if (!data.length) return null
  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Recent Drafts</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
          <thead className="bg-gray-50 text-gray-600 text-left">
            <tr>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Event</th>
              <th className="px-3 py-2">Cube</th>
              <th className="px-3 py-2">Deck</th>
              <th className="px-3 py-2">Colors</th>
              <th className="px-3 py-2 text-right">Record</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.deck_id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-3 py-2 text-gray-500 whitespace-nowrap">
                  {d.date ? new Date(d.date).toLocaleDateString() : '—'}
                </td>
                <td className="px-3 py-2 text-blue-700">
                  <Link to={`/cubes/${d.cube_id}/drafts/${d.draft_event_id}`}>{d.event_name}</Link>
                </td>
                <td className="px-3 py-2 text-blue-700">
                  {d.cube_id ? <Link to={`/cubes/${d.cube_id}`}>{d.cube_name}</Link> : d.cube_name}
                </td>
                <td className="px-3 py-2">
                  <span className="font-medium">{d.deck_name}</span>
                  {d.archetype && (
                    <span className="ml-1 text-xs text-gray-400 capitalize">({d.archetype})</span>
                  )}
                </td>
                <td className="px-3 py-2">
                  <ColorPips identity={d.color_identity} />
                </td>
                <td className="px-3 py-2 text-right font-semibold">{d.record}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { userId } = useParams<{ userId: string }>()
  const { user: authUser } = useAuth()

  const resolvedId = userId ? parseInt(userId) : authUser?.id
  const isOwnProfile = !userId || parseInt(userId) === authUser?.id

  const [stats, setStats] = useState<PlayerStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [cardTab, setCardTab] = useState<'drafted' | 'best'>('drafted')

  useEffect(() => {
    if (!resolvedId) return
    setLoading(true)
    setError(null)
    statisticsApi
      .getPlayerStats(resolvedId)
      .then(setStats)
      .catch(() => setError('Failed to load player stats.'))
      .finally(() => setLoading(false))
  }, [resolvedId])

  if (!resolvedId) return <Layout><p className="text-gray-500">No player selected.</p></Layout>

  if (loading)
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
        </div>
      </Layout>
    )

  if (error || !stats)
    return <Layout><p className="text-red-500">{error ?? 'Player not found.'}</p></Layout>

  const overallWR = pct(stats.overall_win_rate)
  const favArchetype =
    stats.archetype_breakdown[0]?.archetype ?? '—'
  const favColor =
    stats.color_breakdown[0]?.color_identity ?? null

  return (
    <Layout>
    <div className="space-y-8">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl p-6 text-white">
        <div className="flex items-center gap-4">
          <div className="h-16 w-16 rounded-full bg-white/20 flex items-center justify-center text-3xl font-bold">
            {stats.username.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="text-2xl font-bold">{stats.username}</h1>
            {isOwnProfile && <p className="text-blue-200 text-sm">Your profile</p>}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-6 text-sm">
          <span>
            <span className="text-blue-200">Overall record </span>
            <span className="font-semibold text-lg">
              {record(stats.total_wins, stats.total_losses)}
            </span>
          </span>
          <span>
            <span className="text-blue-200">Win rate </span>
            <span className="font-semibold text-lg">{overallWR}</span>
          </span>
          <span>
            <span className="text-blue-200">Drafts </span>
            <span className="font-semibold text-lg">{stats.total_drafts}</span>
          </span>
        </div>
      </div>

      {/* ── Summary stat cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Total Drafts" value={String(stats.total_drafts)} />
        <StatCard label="Win Rate" value={overallWR} />
        <StatCard label="Fav Archetype" value={favArchetype} />
        <StatCard
          label="Fav Colors"
          value={favColor ?? '—'}
        />
      </div>

      {/* ── Best deck highlight ────────────────────────────────────────────── */}
      {stats.best_deck && (
        <section className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-amber-700 uppercase tracking-wide mb-2">
            Best Deck
          </h2>
          <div className="flex flex-wrap items-center gap-4">
            <Link
              to={`/cubes/${stats.best_deck.cube_name ? stats.best_deck.draft_event_id : ''}`}
              className="text-lg font-bold text-gray-900 hover:text-blue-700"
            >
              {stats.best_deck.deck_name}
            </Link>
            <span className="bg-amber-200 text-amber-800 text-sm font-semibold px-2 py-0.5 rounded-full">
              {stats.best_deck.record}
            </span>
            <ColorPips identity={stats.best_deck.color_identity} />
            {stats.best_deck.archetype && (
              <span className="text-sm text-gray-500 capitalize">{stats.best_deck.archetype}</span>
            )}
          </div>
          {stats.best_deck.event_name && (
            <p className="text-sm text-gray-500 mt-1">
              {stats.best_deck.event_name}
              {stats.best_deck.cube_name && ` · ${stats.best_deck.cube_name}`}
            </p>
          )}
          {stats.best_deck.ai_description && (
            <p className="text-sm text-gray-700 mt-2 italic line-clamp-2">
              {stats.best_deck.ai_description}
            </p>
          )}
        </section>
      )}

      {/* ── Cubes played ──────────────────────────────────────────────────── */}
      <CubesPlayedSection data={stats.cubes_played} />

      {/* ── Archetype + Color breakdown ───────────────────────────────────── */}
      {(stats.archetype_breakdown.length > 0 || stats.color_breakdown.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <BreakdownBars
            title="Archetype Breakdown"
            rows={stats.archetype_breakdown.map((a) => ({
              label: a.archetype,
              count: a.count,
              wins: a.wins,
              losses: a.losses,
              win_rate: a.win_rate,
            }))}
          />
          <BreakdownBars
            title="Color Identity Breakdown"
            rows={stats.color_breakdown.map((c) => ({
              label: c.color_identity,
              count: c.count,
              wins: c.wins,
              losses: c.losses,
              win_rate: c.win_rate,
            }))}
          />
        </div>
      )}

      {/* ── Card stats ────────────────────────────────────────────────────── */}
      {(stats.most_drafted_cards.length > 0 || stats.best_cards.length > 0) && (
        <section>
          <div className="flex items-center gap-4 mb-3">
            <h2 className="text-lg font-semibold text-gray-800">Card Stats</h2>
            <div className="flex rounded-md border border-gray-200 overflow-hidden text-sm">
              <button
                onClick={() => setCardTab('drafted')}
                className={`px-3 py-1 ${cardTab === 'drafted' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
              >
                Most Drafted
              </button>
              <button
                onClick={() => setCardTab('best')}
                className={`px-3 py-1 ${cardTab === 'best' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
              >
                Best Win Rate
              </button>
            </div>
          </div>
          {cardTab === 'drafted' ? (
            <CardTable
              cards={stats.most_drafted_cards}
              title="Most Frequently Drafted"
              metric="times_played"
            />
          ) : (
            <CardTable
              cards={stats.best_cards}
              title="Best Win Rate (min 2 drafts)"
              metric="win_rate"
            />
          )}
        </section>
      )}

      {/* ── Head-to-head ──────────────────────────────────────────────────── */}
      <HeadToHeadSection data={stats.head_to_head} />

      {/* ── Recent drafts ─────────────────────────────────────────────────── */}
      <RecentDraftsSection data={stats.recent_drafts} />
    </div>    </Layout>  )
}
