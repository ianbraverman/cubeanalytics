import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { cardsApi } from '../../api/cards'
import Layout from '../../components/Layout'

export default function CardDetailPage() {
  const { cardId } = useParams<{ cardId: string }>()
  const parsedCardId = Number(cardId)

  const { data: cardInfo, isLoading, isError } = useQuery({
    queryKey: ['cardInfo', parsedCardId],
    queryFn: () => cardsApi.getCardInfo(parsedCardId),
    enabled: Number.isFinite(parsedCardId) && parsedCardId > 0,
  })

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
          <Link to="/cubes" className="text-blue-600 hover:text-blue-800">
            ← Back to Cubes
          </Link>
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
      </div>
    </Layout>
  )
}