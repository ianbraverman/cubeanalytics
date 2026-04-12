import apiClient from './client'

export interface Cube {
  id: number
  name: string
  description?: string
  owner_id: number
  created_at: string
  updated_at: string
  // gameplay / pack settings
  life_total: number
  pack_count: number
  pack_size: number
  draft_rules?: string
  gameplay_rules?: string
  cubecobra_link?: string
}

export interface CubeCard {
  id: number
  cube_id: number
  card_id: number
  quantity: number
  card: {
    id: number
    name: string
    scryfall_id: string
    mana_cost?: string
    type_line?: string
    colors?: string[]
    cmc?: number
    power?: string
    toughness?: string
    oracle_text?: string
    image_url?: string
    small_image_url?: string
    rarity?: string
    set_code?: string
    set_name?: string
    scryfall_uri?: string
  }
}

export const cubesApi = {
  createCube: async (data: { name: string; description?: string; cubecobra_link?: string }, ownerId: number) => {
    const response = await apiClient.post<Cube>('/cubes/', data, {
      params: { owner_id: ownerId },
    })
    return response.data
  },

  getCube: async (cubeId: number) => {
    const response = await apiClient.get<Cube>(`/cubes/${cubeId}`)
    return response.data
  },

  getUserCubes: async (ownerId: number) => {
    const response = await apiClient.get<Cube[]>(`/cubes/owner/${ownerId}`)
    return response.data
  },

  getAllCubes: async () => {
    const response = await apiClient.get<Cube[]>('/cubes/')
    return response.data
  },

  updateCube: async (cubeId: number, data: { name: string; description?: string; cubecobra_link?: string }) => {
    const response = await apiClient.put<Cube>(`/cubes/${cubeId}`, data)
    return response.data
  },

  deleteCube: async (cubeId: number) => {
    const response = await apiClient.delete(`/cubes/${cubeId}`)
    return response.data
  },

  // Cube cards operations
  addCardToCube: async (cubeId: number, cardId: number, quantity: number = 1) => {
    const response = await apiClient.post(`/cube-cards/${cubeId}/add-card`, {
      card_id: cardId,
      quantity,
    })
    return response.data
  },

  getCubeCards: async (cubeId: number) => {
    const response = await apiClient.get<CubeCard[]>(`/cube-cards/${cubeId}/cards`)
    return response.data
  },

  removeCardFromCube: async (cubeId: number, cardId: number) => {
    const response = await apiClient.delete(`/cube-cards/${cubeId}/remove-card/${cardId}`)
    return response.data
  },

  clearAllCardsFromCube: async (cubeId: number) => {
    const response = await apiClient.delete(`/cube-cards/${cubeId}/clear-all`)
    return response.data
  },

  updateCubeSettings: async (
    cubeId: number,
    settings: {
      life_total?: number
      pack_count?: number
      pack_size?: number
      draft_rules?: string
      gameplay_rules?: string
    },
  ) => {
    const response = await apiClient.patch<Cube>(`/cubes/${cubeId}/settings`, settings)
    return response.data
  },

  getCubeSize: async (cubeId: number) => {
    const response = await apiClient.get(`/cube-cards/${cubeId}/size`)
    return response.data
  },

  bulkAddCardsToCube: async (cubeId: number, cardIds: number[]) => {
    const response = await apiClient.post<{ added: number; skipped: number }>(
      `/cube-cards/${cubeId}/bulk-add`,
      cardIds,
    )
    return response.data
  },

  decrementCardFromCube: async (cubeId: number, cardId: number) => {
    const response = await apiClient.delete(`/cube-cards/${cubeId}/decrement-card/${cardId}`)
    return response.data
  },
}
