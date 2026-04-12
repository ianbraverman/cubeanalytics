import apiClient from './client'

export interface CardStat {
  card_id: number
  card_name: string
  image_url?: string
  colors: string[]
  cmc?: number
  type_line?: string
  times_maindecked: number
  times_in_pool: number
  times_in_sideboard: number
  times_hate_drafted_or_cut: number
  times_in_winning_deck: number
  total_wins_with: number
  total_losses_with: number
  win_rate: number | null
  inclusion_rate: number | null
  avg_feedback_rating: number | null
  feedback_count: number
  times_standout: number
  times_underperformer: number
}

export interface MacroArchetype {
  name: string
  count: number
  total_wins: number
  total_losses: number
  win_rate: number | null
}

export interface HeadToHead {
  archetype_a: string
  archetype_b: string
  a_wins: number
  b_wins: number
  matches: number
}

export interface ArchetypeStats {
  macro_archetypes: MacroArchetype[]
  detail_archetypes: MacroArchetype[]
  head_to_head: HeadToHead[]
}

export interface ColorPairStat {
  color_identity: string
  count: number
  total_wins: number
  total_losses: number
  win_rate: number | null
}

export interface ColorStats {
  color_pairs: ColorPairStat[]
  color_representation: Record<string, number>
}

export interface MetaHealth {
  total_drafts: number
  total_decks: number
  color_representation: Record<string, number>
  archetype_distribution: Record<string, number>
  avg_cmc_winning_decks: number | null
  avg_cmc_losing_decks: number | null
  dominant_archetype: string | null
  color_diversity_index: number | null
  distinct_color_identities: number
  returning_player_rate: number | null
}

export interface SynergyStat {
  card_a_id: number
  card_a_name: string
  card_b_id: number
  card_b_name: string
  co_occurrences: number
  co_occur_wins: number
  co_occur_losses: number
  win_rate: number | null
}

// ── Player stats ───────────────────────────────────────────────────────────

export interface CubePlayed {
  cube_id: number
  cube_name: string
  draft_count: number
  total_wins: number
  total_losses: number
  win_rate: number | null
}

export interface ArchetypeStat {
  archetype: string
  count: number
  wins: number
  losses: number
  win_rate: number | null
}

export interface ColorStat {
  color_identity: string
  count: number
  wins: number
  losses: number
  win_rate: number | null
}

export interface PlayerCardStat {
  card_id: number
  card_name: string
  times_played: number
  wins_with: number
  losses_with: number
  win_rate: number | null
}

export interface HeadToHead {
  opponent_user_id: number
  opponent_username: string
  wins: number
  losses: number
  matches: number
  win_rate: number | null
}

export interface RecentDraft {
  draft_event_id: number
  deck_id: number
  event_name: string
  cube_id: number | null
  cube_name: string
  deck_name: string
  archetype: string | null
  archetype_detail: string | null
  color_identity: string | null
  wins: number
  losses: number
  record: string
  date: string | null
}

export interface BestDeck {
  deck_id: number
  deck_name: string
  record: string
  wins: number
  losses: number
  archetype: string | null
  archetype_detail: string | null
  color_identity: string | null
  draft_event_id: number
  event_name: string | null
  cube_name: string | null
  ai_description: string | null
}

export interface PlayerStats {
  user_id: number
  username: string
  cube_id: number | null
  total_drafts: number
  total_decks: number
  total_wins: number
  total_losses: number
  overall_win_rate: number | null
  cubes_played: CubePlayed[]
  archetype_breakdown: ArchetypeStat[]
  color_breakdown: ColorStat[]
  most_drafted_cards: PlayerCardStat[]
  best_cards: PlayerCardStat[]
  head_to_head: HeadToHead[]
  recent_drafts: RecentDraft[]
  best_deck: BestDeck | null
}

export const statisticsApi = {
  getCardStats: (cubeId: number) =>
    apiClient.get<CardStat[]>(`/statistics/cubes/${cubeId}/cards`).then((r) => r.data),

  getArchetypeStats: (cubeId: number) =>
    apiClient.get<ArchetypeStats>(`/statistics/cubes/${cubeId}/archetypes`).then((r) => r.data),

  getColorStats: (cubeId: number) =>
    apiClient.get<ColorStats>(`/statistics/cubes/${cubeId}/colors`).then((r) => r.data),

  getMetaHealth: (cubeId: number) =>
    apiClient.get<MetaHealth>(`/statistics/cubes/${cubeId}/meta`).then((r) => r.data),

  getSynergyStats: (cubeId: number, minCoOccurrences = 3) =>
    apiClient
      .get<SynergyStat[]>(`/statistics/cubes/${cubeId}/synergies`, {
        params: { min_co_occurrences: minCoOccurrences },
      })
      .then((r) => r.data),

  getPlayerStats: (userId: number, cubeId?: number) =>
    apiClient
      .get<PlayerStats>(`/statistics/players/${userId}`, {
        params: cubeId !== undefined ? { cube_id: cubeId } : {},
      })
      .then((r) => r.data),
}
