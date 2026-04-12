import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { statisticsApi } from '../../api/statistics'
import type { CardStat } from '../../api/statistics'

interface Props {
  cubeId: number
}

// ─── Helpers ────────────────────────────────────────────────────────────────

const fmtWR = (wr: number | null) =>
  wr === null ? '—' : `${(wr * 100).toFixed(1)}%`

const fmtPct = (n: number) => `${Math.round(n * 100)}%`

const wrColor = (wr: number | null) => {
  if (wr === null) return 'text-gray-400'
  if (wr >= 0.58) return 'text-green-600 font-semibold'
  if (wr >= 0.42) return 'text-gray-600'
  return 'text-red-500'
}

const wrBadge = (wr: number | null) => {
  if (wr === null) return 'bg-gray-100 text-gray-400'
  if (wr >= 0.58) return 'bg-green-100 text-green-700'
  if (wr >= 0.42) return 'bg-gray-100 text-gray-600'
  return 'bg-red-100 text-red-600'
}

const ARCHETYPE_STYLE: Record<string, { bar: string; pill: string }> = {
  aggro:    { bar: 'bg-red-400',     pill: 'bg-red-100 text-red-700' },
  midrange: { bar: 'bg-emerald-500', pill: 'bg-emerald-100 text-emerald-700' },
  control:  { bar: 'bg-blue-500',    pill: 'bg-blue-100 text-blue-700' },
  combo:    { bar: 'bg-purple-500',  pill: 'bg-purple-100 text-purple-700' },
  other:    { bar: 'bg-gray-400',    pill: 'bg-gray-100 text-gray-600' },
}

const getArchetypeStyle = (name: string) => ARCHETYPE_STYLE[name.toLowerCase()] ?? ARCHETYPE_STYLE.other

const COLOR_BAR: Record<string, { fill: string; label: string }> = {
  W: { fill: 'bg-yellow-300', label: 'White' },
  U: { fill: 'bg-blue-500',   label: 'Blue'  },
  B: { fill: 'bg-gray-700',   label: 'Black' },
  R: { fill: 'bg-red-500',    label: 'Red'   },
  G: { fill: 'bg-green-500',  label: 'Green' },
}

// ─── Card Table sub-component ────────────────────────────────────────────────

interface CardTableProps {
  cards: CardStat[]
  cubeId: number
  emptyMsg: string
}

function CardTable({ cards, cubeId, emptyMsg }: CardTableProps) {
  if (cards.length === 0)
    return <p className="text-sm text-gray-400 py-4 text-center">{emptyMsg}</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-gray-400 border-b border-gray-100">
            <th className="text-left pb-2 font-medium">Card</th>
            <th className="text-right pb-2 font-medium">Played</th>
            <th className="text-right pb-2 font-medium">W–L</th>
            <th className="text-right pb-2 font-medium">Win%</th>
            <th className="text-right pb-2 font-medium">Rating</th>
          </tr>
        </thead>
        <tbody>
          {cards.map((card) => (
            <tr key={card.card_id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50 group">
              <td className="py-1.5 pr-2">
                <Link
                  to={`/cards/${card.card_id}?cubeId=${cubeId}`}
                  className="font-medium text-blue-700 hover:text-blue-900 hover:underline"
                >
                  {card.card_name}
                </Link>
                {card.times_standout > 0 && (
                  <span className="ml-1.5 text-xs bg-yellow-100 text-yellow-700 rounded px-1 py-0.5">
                    ⭐ ×{card.times_standout}
                  </span>
                )}
                {card.times_underperformer > 0 && (
                  <span className="ml-1 text-xs bg-orange-100 text-orange-600 rounded px-1 py-0.5">
                    👎 ×{card.times_underperformer}
                  </span>
                )}
              </td>
              <td className="text-right text-gray-500 py-1.5">{card.times_maindecked}</td>
              <td className="text-right text-gray-500 py-1.5">
                {card.total_wins_with}–{card.total_losses_with}
              </td>
              <td className={`text-right py-1.5 ${wrColor(card.win_rate)}`}>
                {fmtWR(card.win_rate)}
              </td>
              <td className="text-right py-1.5">
                {card.avg_feedback_rating !== null ? (
                  <span className="text-yellow-500 text-xs" title={`${card.avg_feedback_rating.toFixed(1)} / 5 (${card.feedback_count} ratings)`}>
                    {'★'.repeat(Math.round(card.avg_feedback_rating))}
                    <span className="text-gray-300">{'★'.repeat(5 - Math.round(card.avg_feedback_rating))}</span>
                  </span>
                ) : (
                  <span className="text-gray-300 text-xs">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function CubeStatsPanel({ cubeId }: Props) {
  const [cardView, setCardView] = useState<'top' | 'popular' | 'bottom'>('top')
  const [showAllH2H, setShowAllH2H] = useState(false)

  const { data: meta, isLoading } = useQuery({
    queryKey: ['stats-meta', cubeId],
    queryFn: () => statisticsApi.getMetaHealth(cubeId),
    staleTime: 60_000,
  })
  const { data: archetypes } = useQuery({
    queryKey: ['stats-archetypes', cubeId],
    queryFn: () => statisticsApi.getArchetypeStats(cubeId),
    staleTime: 60_000,
  })
  const { data: colors } = useQuery({
    queryKey: ['stats-colors', cubeId],
    queryFn: () => statisticsApi.getColorStats(cubeId),
    staleTime: 60_000,
  })
  const { data: cardStats } = useQuery({
    queryKey: ['stats-cards', cubeId],
    queryFn: () => statisticsApi.getCardStats(cubeId),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="text-center py-16 text-gray-500">
        <div className="text-4xl mb-3">📊</div>
        <p>Loading statistics…</p>
      </div>
    )
  }

  if (!meta || meta.total_drafts === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        <div className="text-5xl mb-4">📊</div>
        <p className="text-lg font-medium text-gray-700">No draft data yet</p>
        <p className="text-sm mt-1 text-gray-500">
          Statistics will appear after the first draft event completes.
        </p>
      </div>
    )
  }

  // ── Derived values ──────────────────────────────────────────────────────

  const macroArchetypes = archetypes?.macro_archetypes ?? []
  const maxArchCount = Math.max(...macroArchetypes.map((a) => a.count), 1)

  const played = (cardStats ?? []).filter((c) => c.times_maindecked >= 3)
  const topCards = [...played]
    .sort((a, b) => (b.win_rate ?? -1) - (a.win_rate ?? -1))
    .slice(0, 8)
  const bottomCards = [...played]
    .sort((a, b) => (a.win_rate ?? 2) - (b.win_rate ?? 2))
    .slice(0, 8)
  const popularCards = [...(cardStats ?? [])]
    .sort((a, b) => b.times_maindecked - a.times_maindecked)
    .slice(0, 8)

  const colorPairs = (colors?.color_pairs ?? []).filter((cp) => cp.count >= 1).slice(0, 10)
  const h2hList = archetypes?.head_to_head ?? []
  const visibleH2H = showAllH2H ? h2hList : h2hList.slice(0, 6)

  const topArchetype =
    meta.dominant_archetype ??
    (Object.entries(meta.archetype_distribution ?? {})[0]?.[0] ?? null)

  return (
    <div className="space-y-5">
      {/* ── Summary Cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Drafts</p>
          <p className="text-3xl font-bold text-gray-900">{meta.total_drafts}</p>
          <p className="text-xs text-gray-500 mt-1">{meta.total_decks} total decks</p>
        </div>
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Color Variety</p>
          <p className="text-3xl font-bold text-gray-900">{meta.distinct_color_identities}</p>
          <p className="text-xs text-gray-500 mt-1">distinct combinations</p>
        </div>
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            {meta.dominant_archetype ? 'Dominant' : 'Most Played'}
          </p>
          <p className="text-lg font-bold text-gray-900 capitalize">
            {topArchetype ?? '—'}
          </p>
          {meta.dominant_archetype && (
            <p className="text-xs text-orange-600 mt-1 font-medium">⚠ possible overrepresentation</p>
          )}
        </div>
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Returning Players</p>
          <p className="text-3xl font-bold text-gray-900">
            {meta.returning_player_rate !== null ? fmtPct(meta.returning_player_rate) : '—'}
          </p>
          <p className="text-xs text-gray-500 mt-1">played 2+ events</p>
        </div>
      </div>

      {/* ── Archetype Performance ──────────────────────────────────────── */}
      {macroArchetypes.length > 0 && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide mb-4">
            Archetype Performance
          </h3>
          <div className="space-y-3">
            {macroArchetypes.map((arch) => {
              const style = getArchetypeStyle(arch.name)
              const widthPct = Math.round((arch.count / maxArchCount) * 100)
              return (
                <div key={arch.name} className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700 capitalize w-20 shrink-0">
                    {arch.name}
                  </span>
                  <div className="flex-1 bg-gray-200 rounded-full h-5 overflow-hidden">
                    <div
                      className={`${style.bar} h-full rounded-full transition-all duration-700`}
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-16 text-right shrink-0">
                    {arch.count} deck{arch.count !== 1 ? 's' : ''}
                  </span>
                  <span
                    className={`text-xs font-semibold rounded px-2 py-0.5 w-14 text-center shrink-0 ${wrBadge(arch.win_rate)}`}
                  >
                    {fmtWR(arch.win_rate)}
                  </span>
                </div>
              )
            })}
          </div>

          {(meta.avg_cmc_winning_decks !== null || meta.avg_cmc_losing_decks !== null) && (
            <div className="mt-4 pt-4 border-t border-gray-200 flex flex-wrap gap-6 text-sm">
              <div>
                <span className="text-gray-500">Avg CMC of winning decks: </span>
                <span className="font-semibold text-green-600">
                  {meta.avg_cmc_winning_decks?.toFixed(2) ?? '—'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Avg CMC of losing decks: </span>
                <span className="font-semibold text-red-500">
                  {meta.avg_cmc_losing_decks?.toFixed(2) ?? '—'}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Color Analysis ─────────────────────────────────────────────── */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* W U B R G presence bars */}
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide mb-4">
            Color Presence
          </h3>
          <div className="space-y-2.5">
            {(['W', 'U', 'B', 'R', 'G'] as const).map((c) => {
              const pct = meta.color_representation[c] ?? 0
              const style = COLOR_BAR[c]
              return (
                <div key={c} className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-gray-600 w-10 shrink-0">
                    {style.label}
                  </span>
                  <div className="flex-1 bg-gray-200 rounded-full h-4 overflow-hidden">
                    <div
                      className={`${style.fill} h-full rounded-full transition-all duration-700`}
                      style={{ width: `${Math.round(pct * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-9 text-right shrink-0">
                    {fmtPct(pct)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Color pair win rates */}
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide mb-4">
            Color Pair Win Rates
          </h3>
          {colorPairs.length === 0 ? (
            <p className="text-sm text-gray-400">No data yet</p>
          ) : (
            <div className="space-y-2">
              {colorPairs.map((cp) => (
                <div key={cp.color_identity} className="flex items-center justify-between text-sm">
                  <span className="font-mono font-bold text-gray-800 w-10 shrink-0">
                    {cp.color_identity === 'C' ? '—' : cp.color_identity}
                  </span>
                  <span className="text-gray-400 text-xs flex-1 mx-2">
                    {cp.count} deck{cp.count !== 1 ? 's' : ''} · {cp.total_wins}W {cp.total_losses}L
                  </span>
                  <span className={`font-semibold text-sm shrink-0 ${wrColor(cp.win_rate)}`}>
                    {fmtWR(cp.win_rate)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Card Performance ───────────────────────────────────────────── */}
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">
            Card Performance
          </h3>
          <div className="flex rounded-md border border-gray-200 overflow-hidden text-xs bg-white">
            {(
              [
                ['top', 'Top Win Rate'],
                ['popular', 'Most Played'],
                ['bottom', 'Underperforming'],
              ] as [string, string][]
            ).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setCardView(key as 'top' | 'popular' | 'bottom')}
                className={`px-3 py-1.5 transition-colors ${
                  cardView === key
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {cardView === 'top' && (
          <CardTable
            cards={topCards}
            cubeId={cubeId}
            emptyMsg="Not enough data yet — need ≥3 appearances per card."
          />
        )}
        {cardView === 'popular' && (
          <CardTable
            cards={popularCards}
            cubeId={cubeId}
            emptyMsg="No cards have been played yet."
          />
        )}
        {cardView === 'bottom' && (
          <CardTable
            cards={bottomCards}
            cubeId={cubeId}
            emptyMsg="Not enough data yet — need ≥3 appearances per card."
          />
        )}

        <p className="text-xs text-gray-400 mt-3">
          Win Rate / Top Win Rate views require ≥3 maindecked appearances.
        </p>
      </div>

      {/* ── Head-to-Head Matchups ──────────────────────────────────────── */}
      {h2hList.length > 0 && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide mb-4">
            Archetype Head-to-Head
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-400 border-b border-gray-100">
                  <th className="text-left pb-2 font-medium">Matchup</th>
                  <th className="text-right pb-2 font-medium">Record</th>
                  <th className="text-right pb-2 font-medium pr-1">Matches</th>
                </tr>
              </thead>
              <tbody>
                {visibleH2H.map((h2h, i) => {
                  const aStyle = getArchetypeStyle(h2h.archetype_a)
                  const bStyle = getArchetypeStyle(h2h.archetype_b)
                  return (
                    <tr key={i} className="border-b border-gray-50 last:border-0">
                      <td className="py-2">
                        <span
                          className={`capitalize text-xs font-medium rounded px-1.5 py-0.5 mr-1 ${aStyle.pill}`}
                        >
                          {h2h.archetype_a}
                        </span>
                        <span className="text-gray-400 text-xs mx-0.5">vs</span>
                        <span
                          className={`capitalize text-xs font-medium rounded px-1.5 py-0.5 ml-1 ${bStyle.pill}`}
                        >
                          {h2h.archetype_b}
                        </span>
                      </td>
                      <td className="text-right text-gray-600 py-2 font-mono text-xs">
                        {h2h.a_wins}–{h2h.b_wins}
                      </td>
                      <td className="text-right text-gray-400 py-2 pr-1 text-xs">
                        {h2h.matches}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {h2hList.length > 6 && (
            <button
              onClick={() => setShowAllH2H(!showAllH2H)}
              className="mt-3 text-xs text-indigo-600 hover:text-indigo-800"
            >
              {showAllH2H ? '▲ Show less' : `▼ Show all ${h2hList.length} matchups`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
