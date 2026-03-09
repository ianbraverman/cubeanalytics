import apiClient from './client'

export interface Card {
  id: number
  name: string
  scryfall_id: string
  cached_data?: string
  created_at: string
}

export interface ScryfallCardInfo {
  id: string
  name: string
  mana_cost?: string
  type_line?: string
  colors: string[]
  cmc?: number
  power?: string
  toughness?: string
  text?: string
  image_url?: string
  small_image_url?: string
  rarity?: string
  set?: string
  set_name?: string
  scryfall_uri?: string
}

export const cardsApi = {
  searchScryfall: async (query: string, limit: number = 20) => {
    const response = await apiClient.post('/cards/scryfall/search', null, {
      params: { query, limit },
    })
    return response.data
  },

  fetchFromScryfall: async (cardName: string) => {
    const response = await apiClient.post('/cards/scryfall/fetch-by-name', null, {
      params: { card_name: cardName },
    })
    return response.data
  },

  getCardInfo: async (cardId: number, refresh: boolean = false) => {
    const response = await apiClient.get<ScryfallCardInfo>(`/cards/${cardId}/scryfall-info`, {
      params: { refresh },
    })
    return response.data
  },

  searchCards: async (query: string, limit: number = 20) => {
    const response = await apiClient.get<Card[]>('/cards/search', {
      params: { query, limit },
    })
    return response.data
  },

  getAllCards: async (skip: number = 0, limit: number = 100) => {
    const response = await apiClient.get<Card[]>('/cards/', {
      params: { skip, limit },
    })
    return response.data
  },

  bulkFetchAndStoreCards: async (cardNames: string[]) => {
    const response = await apiClient.post<{
      cards: { id: number; name: string }[]
      not_found: string[]
    }>('/cards/scryfall/bulk-fetch-by-names', cardNames)
    return response.data
  },
}
