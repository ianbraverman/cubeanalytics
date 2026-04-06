import apiClient from './client'

// ── Types ──────────────────────────────────────────────────────────────────

export interface UserDeck {
  id: number
  user_id: number
  draft_event_id: number
  player_name?: string
  deck_name?: string
  deck_cards: number[]         // card IDs
  sideboard_cards?: number[]
  full_pool_cards?: number[]
  wins: number
  losses: number
  record?: string              // e.g. "3-0"
  deck_photo_url?: string
  pool_photo_url?: string
  ai_description?: string
  created_at: string
}

export interface DraftParticipant {
  user_id: number
  username: string
  joined_at: string
}

export interface DraftEvent {
  id: number
  cube_id: number
  name?: string
  status?: string              // active | seating_assigned | drafting | deck_submission | in_rounds | completed
  num_players?: number
  ai_summary?: string
  event_type: string           // casual | hosted
  num_rounds?: number
  best_of: number              // 1, 3, 5
  current_round: number
  created_at: string
  updated_at: string
  user_decks?: UserDeck[]
  participants?: DraftParticipant[]
}

export interface CreateDraftPayload {
  cube_id: number
  password: string
  name?: string
  num_players?: number
  event_type?: string    // casual | hosted
  num_rounds?: number
  best_of?: number       // 1, 3, 5
}

// ── Hosted event types ────────────────────────────────────────────────────────

export interface DraftSeat {
  user_id: number
  username: string
  seat_number: number
}

export interface DraftPairing {
  id: number
  player1_user_id?: number
  player2_user_id?: number
  player1_name?: string
  player2_name?: string
  player1_deck_id?: number
  player2_deck_id?: number
  player1_wins: number
  player2_wins: number
  winner_user_id?: number
  player1_confirmed: string
  player2_confirmed: string
  status: string
}

export interface DraftRound {
  id: number
  round_number: number
  status: string
  pairings: DraftPairing[]
}

export interface RoundFeedback {
  id: number
  pairing_id: number
  user_id: number
  liked_card_ids: number[]
  disliked_card_ids: number[]
  liked_notes?: string
  disliked_notes?: string
  general_thoughts?: string
  created_at: string
}

export interface PostDraftFeedback {
  id: number
  draft_event_id: number
  user_id?: number
  player_name?: string
  overall_rating?: number
  overall_thoughts?: string
  standout_card_ids: number[]
  underperformer_card_ids: number[]
  recommendations_for_owner?: string
  created_at: string
}

export interface UpdateDraftPayload {
  name?: string
  status?: string
  num_players?: number
  ai_summary?: string
}

export interface CreateDeckPayload {
  draft_event_id: number
  user_id?: number
  player_name?: string
  deck_name?: string
  deck_cards?: number[]
  sideboard_cards?: number[]
  full_pool_cards?: number[]
  wins?: number
  losses?: number
  record?: string
}

export interface UpdateDeckPayload {
  player_name?: string
  deck_name?: string
  deck_cards?: number[]
  sideboard_cards?: number[]
  full_pool_cards?: number[]
  wins?: number
  losses?: number
  record?: string
  deck_photo_url?: string
  ai_description?: string
}

// ── API functions ───────────────────────────────────────────────────────────

export const draftsApi = {
  // Draft events
  getDraftsForCube: (cubeId: number): Promise<DraftEvent[]> =>
    apiClient.get(`/draft-events/cube/${cubeId}`).then((r) => r.data),

  getDraft: (draftId: number): Promise<DraftEvent> =>
    apiClient.get(`/draft-events/${draftId}`).then((r) => r.data),

  createDraft: (payload: CreateDraftPayload, createdByUserId?: number): Promise<DraftEvent> =>
    apiClient.post('/draft-events/', payload, { params: createdByUserId ? { created_by_user_id: createdByUserId } : {} }).then((r) => r.data),

  updateDraft: (draftId: number, payload: UpdateDraftPayload): Promise<DraftEvent> =>
    apiClient.patch(`/draft-events/${draftId}`, payload).then((r) => r.data),

  changePassword: (draftId: number, newPassword: string): Promise<{ message: string }> =>
    apiClient.patch(`/draft-events/${draftId}/password`, null, { params: { new_password: newPassword } }).then((r) => r.data),

  deleteDraft: (draftId: number): Promise<void> =>
    apiClient.delete(`/draft-events/${draftId}`).then((r) => r.data),

  // Decks
  getDecks: (draftId: number): Promise<UserDeck[]> =>
    apiClient.get(`/draft-events/${draftId}/decks`).then((r) => r.data),

  createDeck: (draftId: number, payload: CreateDeckPayload): Promise<UserDeck> =>
    apiClient.post(`/draft-events/${draftId}/decks`, payload).then((r) => r.data),

  updateDeck: (draftId: number, deckId: number, payload: UpdateDeckPayload): Promise<UserDeck> =>
    apiClient.patch(`/draft-events/${draftId}/decks/${deckId}`, payload).then((r) => r.data),

  deleteDeck: (draftId: number, deckId: number): Promise<void> =>
    apiClient.delete(`/draft-events/${draftId}/decks/${deckId}`).then((r) => r.data),

  // Photo upload
  uploadDeckPhoto: (draftId: number, deckId: number, file: File, analyze = false): Promise<{ deck_photo_url: string; identified_cards?: string[]; ai_error?: string }> => {
    const form = new FormData()
    form.append('file', file)
    return apiClient
      .post(`/draft-events/${draftId}/decks/${deckId}/photo?analyze=${analyze}`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  // AI
  // Dual-photo analysis (deck + pool)
  analyzePhotos: (
    draftId: number,
    deckId: number,
    deckFile: File,
    poolFile: File | null,
  ): Promise<{
    deck_photo_url: string
    pool_photo_url: string | null
    deck_identified: string[]
    pool_identified: string[]
    sideboard_identified: string[]
    ai_error?: string
  }> => {
    const form = new FormData()
    form.append('deck_file', deckFile)
    if (poolFile) form.append('pool_file', poolFile)
    return apiClient
      .post(`/draft-events/${draftId}/decks/${deckId}/analyze-photos`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  generateDeckAI: (draftId: number, deckId: number): Promise<{ ai_description: string }> =>
    apiClient.post(`/draft-events/${draftId}/decks/${deckId}/ai-description`).then((r) => r.data),

  generateDraftAI: (draftId: number): Promise<{ ai_summary: string }> =>
    apiClient.post(`/draft-events/${draftId}/ai-summary`).then((r) => r.data),

  joinDraft: (draftId: number, password: string, userId?: number): Promise<{ message: string }> =>
    apiClient.post(`/draft-events/${draftId}/verify-password`, null, {
      params: { password, ...(userId ? { user_id: userId } : {}) },
    }).then((r) => r.data),

  // ── Hosted event endpoints ──────────────────────────────────────────────

  /** Randomly assign seats and move status → seating_assigned */
  startEvent: (draftId: number): Promise<{ seats: DraftSeat[] }> =>
    apiClient.post(`/draft-events/${draftId}/start`).then((r) => r.data),

  getSeating: (draftId: number): Promise<DraftSeat[]> =>
    apiClient.get(`/draft-events/${draftId}/seating`).then((r) => r.data),

  /** Advance event to next status phase */
  advanceStatus: (draftId: number): Promise<DraftEvent> =>
    apiClient.post(`/draft-events/${draftId}/advance`).then((r) => r.data),

  /** Generate Swiss pairings for the next round */
  startNextRound: (draftId: number): Promise<DraftRound> =>
    apiClient.post(`/draft-events/${draftId}/next-round`).then((r) => r.data),

  getRound: (draftId: number, roundNumber: number): Promise<DraftRound> =>
    apiClient.get(`/draft-events/${draftId}/rounds/${roundNumber}`).then((r) => r.data),

  getAllRounds: (draftId: number): Promise<DraftRound[]> =>
    apiClient.get(`/draft-events/${draftId}/rounds`).then((r) => r.data),

  /** Submit or update match result for a pairing (dual-player confirmation) */
  submitMatchResult: (
    draftId: number,
    pairingId: number,
    payload: { player1_wins: number; player2_wins: number },
    userId?: number,
  ): Promise<DraftPairing> =>
    apiClient.patch(
      `/draft-events/${draftId}/pairings/${pairingId}/result`,
      payload,
      { params: userId ? { user_id: userId } : {} },
    ).then((r) => r.data),

  submitRoundFeedback: (
    draftId: number,
    pairingId: number,
    payload: {
      liked_card_ids?: number[]
      disliked_card_ids?: number[]
      liked_notes?: string
      disliked_notes?: string
      general_thoughts?: string
    },
  ): Promise<RoundFeedback> =>
    apiClient.post(`/draft-events/${draftId}/pairings/${pairingId}/feedback`, payload).then((r) => r.data),

  getRoundFeedback: (draftId: number, pairingId: number): Promise<RoundFeedback[]> =>
    apiClient.get(`/draft-events/${draftId}/pairings/${pairingId}/feedback`).then((r) => r.data),

  submitPostDraftFeedback: (
    draftId: number,
    payload: {
      player_name?: string
      overall_rating?: number
      overall_thoughts?: string
      standout_card_ids?: number[]
      underperformer_card_ids?: number[]
      recommendations_for_owner?: string
    },
    userId?: number,
  ): Promise<PostDraftFeedback> => {
    const params = userId != null ? `?user_id=${userId}` : ''
    return apiClient.post(`/draft-events/${draftId}/post-draft-feedback${params}`, payload).then((r) => r.data)
  },

  getPostDraftFeedback: (draftId: number): Promise<PostDraftFeedback[]> =>
    apiClient.get(`/draft-events/${draftId}/post-draft-feedback`).then((r) => r.data),

  /** Cube-owner full summary (decks, standings, card tally, AI analysis) */
  getFullSummary: (draftId: number): Promise<Record<string, unknown>> =>
    apiClient.get(`/draft-events/${draftId}/full-summary`).then((r) => r.data),

  /** All drafts the user has participated in */
  getDraftsForUser: (userId: number): Promise<UserDraftSummary[]> =>
    apiClient.get(`/draft-events/user/${userId}`).then((r) => r.data),
}

// ── User-centric draft summary (returned by /user/{user_id}) ────────────────
export interface UserDraftSummary {
  id: number
  cube_id: number
  cube_name?: string
  name?: string
  status?: string
  event_type: string
  num_rounds?: number
  best_of: number
  current_round: number
  created_at: string
  joined_at?: string
  my_deck?: {
    id: number
    player_name?: string
    deck_name?: string
    wins: number
    losses: number
    record?: string
    ai_description?: string
  } | null
}
