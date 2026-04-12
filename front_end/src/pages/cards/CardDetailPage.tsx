import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { cardsApi } from '../../api/cards'
import { statisticsApi } from '../../api/statistics'
import Layout from '../../components/Layout'

export default function CardDetailPage() {
  const { cardId } = useParams<{ cardId: string }>()
  const [searchParams] = useSearchParams()
  const parsedCardId = Number(cardId)
  const cubeId = searchParams.get('cubeId') ? parseInt(searchParams.get('cubeId')!) : null

  const { data: cardInfo, isLoading, isError } = useQuery({
    queryKey: ['cardInfo', parsedCardId],
    queryFn: () => cardsApi.getCardInfo(parsedCardId),
    enabled: Number.isFinite(parsedCardId) && parsedCardId > 0,
  })

  const { data: cardStats } = useQuery({
    queryKey: ['stats-cards', cubeId],
    queryFn: () => statisticsApi.getCardStats(cubeId!),
    enabled: cubeId !== null,
    staleTime: 60_000,
  })

  const cardStat = cardStats?.find((s) => s.card_id === parsedCardId) ?? null

  if (isLoading) {
    return (
      <Layout>
        <div className="text-center py-12 text-gray-600">Loading card details...</div>
      </Layout>
    )
  }

  if (isError || !cardInfo) {
    return (
      <Layout>
        <div className="bg-white rounded-lg shadow-md p-8">
          <p className="text-gray-700 mb-4">Unable to load this card.</p>
          <Link to="/cubes" className="text-blue-600 hover:text-blue-800">
            Back to Cubes
          </Link>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="mb-6">
          {cubeId ? (
            <Link to={`/cubes/${cubeId}`} className="text-blue-600 hover:text-blue-800">
              ← Back to Cube
            </Link>
          ) : (
            <Link to="/cubes" className="text-blue-600 hover:text-blue-800">
              ← Back to Cubes
            </Link>
          )}
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          <div className="lg:w-1/3">
            {cardInfo.image_url ? (
              <img
                src={cardInfo.image_url}
                alt={cardInfo.name}
                className="w-full max-w-sm rounded-lg shadow-md"
              />
            ) : (
              <div className="w-full max-w-sm h-96 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500">
                No image available
              </div>
            )}
          </div>

          <div className="lg:w-2/3">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{cardInfo.name}</h1>
            {cardInfo.mana_cost && <p className="text-lg text-gray-700 mb-2">{cardInfo.mana_cost}</p>}
            {cardInfo.type_line && <p className="text-gray-700 mb-4">{cardInfo.type_line}</p>}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-500">Mana Value</p>
                <p className="text-gray-900 font-semibold">{cardInfo.cmc ?? 'N/A'}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-500">Colors</p>
                <p className="text-gray-900 font-semibold">
                  {cardInfo.colors && cardInfo.colors.length > 0 ? cardInfo.colors.join(', ') : 'Colorless'}
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-500">Power / Toughness</p>
                <p className="text-gray-900 font-semibold">
                  {cardInfo.power && cardInfo.toughness ? `${cardInfo.power}/${cardInfo.toughness}` : 'N/A'}
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-500">Set</p>
                <p className="text-gray-900 font-semibold">
                  {cardInfo.set_name ? `${cardInfo.set_name} (${cardInfo.set?.toUpperCase()})` : 'N/A'}
                </p>
              </div>
            </div>

            {cardInfo.text && (
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-2">Oracle Text</h2>
                <p className="text-gray-700 whitespace-pre-line">{cardInfo.text}</p>
              </div>
            )}

            {cardInfo.scryfall_uri && (
              <a
                href={cardInfo.scryfall_uri}
                target="_blank"
                rel="noreferrer"
                className="inline-block bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
              >
                View on Scryfall
              </a>
            )}
          </div>
        </div>

        {/* ── Cube Performance ── */}
        {cubeId && cardStat && (
          <div className="mt-6 border-t border-gray-100 pt-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Cube Performance
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              {/* Win Rate */}
              <div className={`rounded-lg p-4 border ${
                cardStat.win_rate === null
                  ? 'bg-gray-50 border-gray-200'
                  : cardStat.win_rate >= 0.58
                  ? 'bg-green-50 border-green-200'
                  : cardStat.win_rate >= 0.42
                  ? 'bg-gray-50 border-gray-200'
                  : 'bg-red-50 border-red-200'
              }`}>
                <p className="text-xs text-gray-500 mb-1">Win Rate</p>
                <p className={`text-2xl font-bold ${
                  cardStat.win_rate === null ? 'text-gray-400'
                  : cardStat.win_rate >= 0.58 ? 'text-green-600'
                  : cardStat.win_rate >= 0.42 ? 'text-gray-700'
                  : 'text-red-600'
                }`}>
                  {cardStat.win_rate !== null
                    ? `${(cardStat.win_rate * 100).toFixed(1)}%`
                    : '—'}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {cardStat.total_wins_with}W – {cardStat.total_losses_with}L
                </p>
              </div>

              {/* Times Played */}
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
                <p className="text-xs text-gray-500 mb-1">Times Maindecked</p>
                <p className="text-2xl font-bold text-gray-900">{cardStat.times_maindecked}</p>
                {cardStat.times_in_pool > 0 && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    {cardStat.inclusion_rate !== null
                      ? `${(cardStat.inclusion_rate * 100).toFixed(0)}% inclusion`
                      : `of ${cardStat.times_in_pool} drafts`}
                  </p>
                )}
              </div>

              {/* Feedback Rating */}
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
                <p className="text-xs text-gray-500 mb-1">Avg Rating</p>
                {cardStat.avg_feedback_rating !== null ? (
                  <>
                    <p className="text-2xl font-bold text-yellow-500">
                      {cardStat.avg_feedback_rating.toFixed(1)}
                      <span className="text-sm text-gray-400 font-normal"> / 5</span>
                    </p>
                    <p className="text-xs text-yellow-500 mt-0.5">
                      {'★'.repeat(Math.round(cardStat.avg_feedback_rating))}
                      <span className="text-gray-300">
                        {'★'.repeat(5 - Math.round(cardStat.avg_feedback_rating))}
                      </span>
                    </p>
                  </>
                ) : (
                  <p className="text-2xl font-bold text-gray-400">—</p>
                )}
                {cardStat.feedback_count > 0 && (
                  <p className="text-xs text-gray-400">{cardStat.feedback_count} rating{cardStat.feedback_count !== 1 ? 's' : ''}</p>
                )}
              </div>

              {/* Nominations */}
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
                <p className="text-xs text-gray-500 mb-2">Player Nominations</p>
                <div className="flex flex-col gap-1">
                  <span className="text-sm">
                    <span className="text-yellow-600 font-semibold">⭐ {cardStat.times_standout}</span>
                    <span className="text-gray-500 ml-1">standout</span>
                  </span>
                  <span className="text-sm">
                    <span className="text-orange-600 font-semibold">👎 {cardStat.times_underperformer}</span>
                    <span className="text-gray-500 ml-1">underperformer</span>
                  </span>
                </div>
              </div>
            </div>

            {/* Draft pool vs hate-drafted note */}
            {cardStat.times_hate_drafted_or_cut > 0 && (
              <p className="text-sm text-gray-500 bg-yellow-50 border border-yellow-200 rounded px-3 py-2">
                ⚠ Drafted but not played in <strong>{cardStat.times_hate_drafted_or_cut}</strong> deck
                {cardStat.times_hate_drafted_or_cut !== 1 ? 's' : ''} — possible hate-draft or sideboard cut.
              </p>
            )}
          </div>
        )}

        {/* Loading state for cube stats */}
        {cubeId && !cardStat && cardStats !== undefined && (
          <div className="mt-6 border-t border-gray-100 pt-6">
            <p className="text-sm text-gray-400">This card has not been played in any draft yet.</p>
          </div>
        )}
      </div>
    </Layout>
  )
}