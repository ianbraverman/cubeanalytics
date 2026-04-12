import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cubesApi } from '../../api/cubes'
import { cardsApi } from '../../api/cards'
import Layout from '../../components/Layout'
import { useAuth } from '../../auth/AuthProvider'
import CubeStatsPanel from './CubeStatsPanel'

export default function CubeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const cubeId = parseInt(id!)
  const { user } = useAuth()
  const [isAddingCards, setIsAddingCards] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [activeTab, setActiveTab] = useState<'cards' | 'stats'>('cards')
  const [settingsLifeTotal, setSettingsLifeTotal] = useState(20)
  const [settingsPackCount, setSettingsPackCount] = useState(3)
  const [settingsPackSize, setSettingsPackSize] = useState(15)
  const [settingsDraftRules, setSettingsDraftRules] = useState('')
  const [settingsGameplayRules, setSettingsGameplayRules] = useState('')
  const [isBulkUpload, setIsBulkUpload] = useState(false)
  const [addSearchText, setAddSearchText] = useState('')
  const [addResults, setAddResults] = useState<any[]>([])
  const [stagedAddCard, setStagedAddCard] = useState<any | null>(null)
  const [removeSearchText, setRemoveSearchText] = useState('')
  const [stagedRemoveCard, setStagedRemoveCard] = useState<any | null>(null)
  const [isReplacing, setIsReplacing] = useState(false)
  const [bulkCardList, setBulkCardList] = useState('')
  const [isProcessingBulk, setIsProcessingBulk] = useState(false)
  const [uploadResult, setUploadResult] = useState<{
    added: number
    notFound: string[]
  } | null>(null)

  // Card image tooltip on hover
  const [tooltip, setTooltip] = useState<{ imageUrl: string; x: number; y: number } | null>(null)
  const tooltipTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleCardMouseEnter = (imageUrl: string | undefined, e: React.MouseEvent) => {
    if (!imageUrl) return
    const x = e.clientX
    const y = e.clientY
    tooltipTimer.current = setTimeout(() => setTooltip({ imageUrl, x, y }), 500)
  }
  const handleCardMouseMove = (e: React.MouseEvent) => {
    if (tooltip) setTooltip((t) => t ? { ...t, x: e.clientX, y: e.clientY } : null)
  }
  const handleCardMouseLeave = () => {
    if (tooltipTimer.current) clearTimeout(tooltipTimer.current)
    setTooltip(null)
  }

  const { data: cube, isLoading: cubeLoading } = useQuery({
    queryKey: ['cube', cubeId],
    queryFn: () => cubesApi.getCube(cubeId),
  })

  const { data: cubeCards, isLoading: cardsLoading } = useQuery({
    queryKey: ['cubeCards', cubeId],
    queryFn: () => cubesApi.getCubeCards(cubeId),
  })

  const { data: cubeSize } = useQuery({
    queryKey: ['cubeSize', cubeId],
    queryFn: () => cubesApi.getCubeSize(cubeId),
  })

  const isOwner = !!(user && cube && cube.owner_id === user.id)

  // Show upload result banner when navigating here from CreateCubePage
  useEffect(() => {
    const state = location.state as { uploadResult?: { added: number; notFound: string[] } } | null
    if (state?.uploadResult) {
      setUploadResult(state.uploadResult)
      // Clear the state so the banner doesn't reappear on refresh
      window.history.replaceState({}, '')
    }
  }, [])

  // Sync settings fields when cube loads
  useEffect(() => {
    if (cube) {
      setSettingsLifeTotal(cube.life_total ?? 20)
      setSettingsPackCount(cube.pack_count ?? 3)
      setSettingsPackSize(cube.pack_size ?? 15)
      setSettingsDraftRules(cube.draft_rules ?? '')
      setSettingsGameplayRules(cube.gameplay_rules ?? '')
    }
  }, [cube?.id])

  const [isEditingInfo, setIsEditingInfo] = useState(false)
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editCubecobraLink, setEditCubecobraLink] = useState('')

  const updateSettingsMutation = useMutation({
    mutationFn: () =>
      cubesApi.updateCubeSettings(cubeId, {
        life_total: settingsLifeTotal,
        pack_count: settingsPackCount,
        pack_size: settingsPackSize,
        draft_rules: settingsDraftRules || undefined,
        gameplay_rules: settingsGameplayRules || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cube', cubeId] })
      setShowSettings(false)
    },
  })

  const deleteCubeMutation = useMutation({
    mutationFn: () => cubesApi.deleteCube(cubeId),
    onSuccess: () => {
      navigate('/cubes')
    },
  })

  const updateInfoMutation = useMutation({
    mutationFn: () =>
      cubesApi.updateCube(cubeId, {
        name: editName,
        description: editDescription || undefined,
        cubecobra_link: editCubecobraLink || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cube', cubeId] })
      setIsEditingInfo(false)
    },
  })

  const clearCardsMutation = useMutation({
    mutationFn: () => cubesApi.clearAllCardsFromCube(cubeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cubeCards', cubeId] })
      queryClient.invalidateQueries({ queryKey: ['cubeSize', cubeId] })
      alert('All cards removed from cube!')
    },
  })

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this cube?')) {
      deleteCubeMutation.mutate()
    }
  }

  const handleClearCards = () => {
    if (window.confirm('Are you sure you want to delete all cards from this cube?')) {
      clearCardsMutation.mutate()
    }
  }

  const handleAddSearch = async () => {
    if (!addSearchText.trim()) return

    try {
      const results = await cardsApi.searchScryfall(addSearchText, 10)
      setAddResults(results.results || [])
    } catch (error) {
      console.error('Error searching Scryfall:', error)
    }
  }

  const COLORS = ['White', 'Blue', 'Black', 'Red', 'Green', 'Colorless', 'Multicolored', 'Lands'] as const
  type ColorKey = typeof COLORS[number]
  const MONO_COLORS = ['White', 'Blue', 'Black', 'Red', 'Green', 'Colorless'] as const
  type MonoColorKey = typeof MONO_COLORS[number]

  const TYPE_ORDER = ['Creature', 'Planeswalker', 'Instant', 'Sorcery', 'Enchantment', 'Artifact', 'Other'] as const
  type TypeKey = typeof TYPE_ORDER[number]

  const COLOR_STYLES: Record<ColorKey, string> = {
    White:       'bg-yellow-50  border-yellow-300',
    Blue:        'bg-blue-50    border-blue-300',
    Black:       'bg-gray-100   border-gray-400',
    Red:         'bg-red-50     border-red-300',
    Green:       'bg-green-50   border-green-300',
    Colorless:   'bg-slate-50   border-slate-300',
    Multicolored:'bg-orange-50  border-orange-300',
    Lands:       'bg-amber-50   border-amber-300',
  }

  // WUBRG canonical order helpers
  const WUBRG = ['W', 'U', 'B', 'R', 'G']
  const genCombos = (size: number): string[] => {
    const result: string[] = []
    const pick = (start: number, chosen: string[]) => {
      if (chosen.length === size) { result.push(chosen.join('')); return }
      for (let i = start; i < WUBRG.length; i++) pick(i + 1, [...chosen, WUBRG[i]])
    }
    pick(0, [])
    return result
  }
  // All multi-color group keys in WUBRG order: 2-color pairs, then 3, 4, 5; 'C' = colorless lands
  const ALL_COLOR_GROUPS = ['W', 'U', 'B', 'R', 'G', ...genCombos(2), ...genCombos(3), ...genCombos(4), ...genCombos(5), 'C']
  const canonicalKey = (colors?: string[]) =>
    !colors || colors.length === 0
      ? 'C'
      : [...colors].sort((a, b) => WUBRG.indexOf(a) - WUBRG.indexOf(b)).join('')

  // Parse produced mana colors from oracle text.
  // Covers two patterns:
  //   1. "{T}: Add {R} or {G}" — explicit mana symbols after "Add"
  //   2. "Search … for a Forest or Plains card" — basic land type words anywhere in text
  const LAND_TYPE_COLOR: Record<string, string> = {
    plains: 'W', island: 'U', swamp: 'B', mountain: 'R', forest: 'G',
  }
  const getManaProduced = (oracleText?: string): string[] => {
    if (!oracleText) return []
    const produced = new Set<string>()
    // Pattern 1: mana symbols on lines containing "Add"
    const addLines = oracleText.split('\n').filter((l) => /\bAdd\b/i.test(l))
    for (const line of addLines) {
      const matches = line.matchAll(/\{([WUBRG])\}/g)
      for (const m of matches) produced.add(m[1])
    }
    // Pattern 2: basic land type names anywhere in oracle text
    const lower = oracleText.toLowerCase()
    for (const [word, color] of Object.entries(LAND_TYPE_COLOR)) {
      if (new RegExp(`\\b${word}\\b`).test(lower)) produced.add(color)
    }
    return [...produced].sort((a, b) => WUBRG.indexOf(a) - WUBRG.indexOf(b))
  }

  const getColorCategory = (colors?: string[], typeLine?: string): ColorKey => {
    if (typeLine && typeLine.toLowerCase().includes('land')) return 'Lands'
    if (!colors || colors.length === 0) return 'Colorless'
    if (colors.length === 1) {
      const colorMap: Record<string, ColorKey> = { W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green' }
      return colorMap[colors[0]] || 'Colorless'
    }
    return 'Multicolored'
  }

  const getTypeCategory = (typeLine?: string): TypeKey => {
    if (!typeLine) return 'Other'
    const t = typeLine.toLowerCase()
    if (t.includes('creature'))     return 'Creature'
    if (t.includes('planeswalker')) return 'Planeswalker'
    if (t.includes('instant'))      return 'Instant'
    if (t.includes('sorcery'))      return 'Sorcery'
    if (t.includes('enchantment'))  return 'Enchantment'
    if (t.includes('artifact'))     return 'Artifact'
    return 'Other'
  }

  type CubeCardList = NonNullable<typeof cubeCards>

  // Organize cards:
  //   mono-color / Colorless  → byType[color][TypeKey][]
  //   Multicolored / Lands    → byCombo[color][canonicalColorKey][]
  const organizeCards = (cards: typeof cubeCards) => {
    const emptyTypeBuckets = (): Record<TypeKey, CubeCardList> => ({
      Creature: [], Planeswalker: [], Instant: [], Sorcery: [], Enchantment: [], Artifact: [], Other: [],
    })
    const byType: Record<MonoColorKey, Record<TypeKey, CubeCardList>> = {
      White: emptyTypeBuckets(), Blue: emptyTypeBuckets(), Black: emptyTypeBuckets(),
      Red:   emptyTypeBuckets(), Green: emptyTypeBuckets(), Colorless: emptyTypeBuckets(),
    }
    const byCombo: Record<'Multicolored' | 'Lands', Record<string, CubeCardList>> = {
      Multicolored: {}, Lands: {},
    }

    cards?.forEach((cubeCard) => {
      if (!cubeCard.card) return
      const color = getColorCategory(cubeCard.card.colors, cubeCard.card.type_line)
      if (color === 'Multicolored' || color === 'Lands') {
        const key = color === 'Lands'
          ? canonicalKey(getManaProduced(cubeCard.card.oracle_text))
          : canonicalKey(cubeCard.card.colors)
        if (!byCombo[color][key]) byCombo[color][key] = []
        byCombo[color][key].push(cubeCard)
      } else {
        const type = getTypeCategory(cubeCard.card.type_line)
        byType[color as MonoColorKey][type].push(cubeCard)
      }
    })

    // sort every bucket by cmc
    for (const color of MONO_COLORS)
      for (const type of TYPE_ORDER)
        byType[color][type].sort((a, b) => (a.card?.cmc ?? 0) - (b.card?.cmc ?? 0))
    for (const col of ['Multicolored', 'Lands'] as const)
      for (const key of Object.keys(byCombo[col]))
        byCombo[col][key].sort((a, b) => (a.card?.cmc ?? 0) - (b.card?.cmc ?? 0))

    return { byType, byCombo }
  }

  const handleAddCard = async (scryfallCard: any) => {
    try {
      const result = await cardsApi.fetchFromScryfall(scryfallCard.name)
      await cubesApi.addCardToCube(cubeId, result.card.id, 1)
      queryClient.invalidateQueries({ queryKey: ['cubeCards', cubeId] })
      queryClient.invalidateQueries({ queryKey: ['cubeSize', cubeId] })
      setStagedAddCard(scryfallCard)
    } catch (error: any) {
      alert(`Error adding card: ${error.message}`)
    }
  }

  const handleDecrementCard = async (cubeCard: any) => {
    try {
      await cubesApi.decrementCardFromCube(cubeId, cubeCard.card_id)
      queryClient.invalidateQueries({ queryKey: ['cubeCards', cubeId] })
      queryClient.invalidateQueries({ queryKey: ['cubeSize', cubeId] })
      setStagedRemoveCard(cubeCard)
    } catch (error: any) {
      alert(`Error removing card: ${error.message}`)
    }
  }

  const handleReplaceCard = async () => {
    if (!stagedAddCard || !stagedRemoveCard) return
    setIsReplacing(true)
    try {
      const result = await cardsApi.fetchFromScryfall(stagedAddCard.name)
      await cubesApi.addCardToCube(cubeId, result.card.id, 1)
      await cubesApi.decrementCardFromCube(cubeId, stagedRemoveCard.card_id)
      queryClient.invalidateQueries({ queryKey: ['cubeCards', cubeId] })
      queryClient.invalidateQueries({ queryKey: ['cubeSize', cubeId] })
      setStagedAddCard(null)
      setStagedRemoveCard(null)
      setAddSearchText('')
      setAddResults([])
      setRemoveSearchText('')
    } catch (err: any) {
      alert(`Replace failed: ${(err as any).response?.data?.detail || (err as any).message}`)
    } finally {
      setIsReplacing(false)
    }
  }

  const handleBulkUpload = async () => {
    if (!bulkCardList.trim()) {
      alert('Please enter some card names')
      return
    }

    setIsProcessingBulk(true)
    const cardNames = bulkCardList
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0)

    try {
      // Bulk-fetch all cards from Scryfall and store them in the DB
      const fetchResult = await cardsApi.bulkFetchAndStoreCards(cardNames)

      // Bulk-add all found cards to the cube
      let added = 0
      if (fetchResult.cards.length > 0) {
        const addResult = await cubesApi.bulkAddCardsToCube(
          cubeId,
          fetchResult.cards.map((c) => c.id),
        )
        added = addResult.added
      }

      // Refresh queries
      queryClient.invalidateQueries({ queryKey: ['cubeCards', cubeId] })
      queryClient.invalidateQueries({ queryKey: ['cubeSize', cubeId] })

      setBulkCardList('')
      setUploadResult({ added, notFound: fetchResult.not_found })
    } catch (err: any) {
      setUploadResult({ added: 0, notFound: [] })
      alert(`Bulk upload failed: ${(err as any).response?.data?.detail || (err as any).message}`)
    } finally {
      setIsProcessingBulk(false)
    }
  }

  if (cubeLoading) {
    return (
      <Layout>
        <div className="text-center py-12">
          <p className="text-gray-600">Loading cube...</p>
        </div>
      </Layout>
    )
  }

  if (!cube) {
    return (
      <Layout>
        <div className="text-center py-12">
          <p className="text-gray-600">Cube not found</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div>
        {/* ── Upload result banner ── */}
        {uploadResult && (
          <div className={`rounded-lg border px-5 py-4 mb-6 ${
            uploadResult.notFound.length > 0
              ? 'bg-yellow-50 border-yellow-300'
              : 'bg-green-50 border-green-300'
          }`}>
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold text-gray-800 mb-1">Bulk Upload Complete</p>
                <p className="text-sm text-gray-700">✅ Added: {uploadResult.added}</p>
                {uploadResult.notFound.length > 0 && (
                  <>
                    <p className="text-sm text-yellow-700 mt-1">
                      ⚠️ Not found on Scryfall: {uploadResult.notFound.length}
                    </p>
                    <ul className="mt-1 ml-4 list-disc text-sm text-yellow-800">
                      {uploadResult.notFound.map((name) => (
                        <li key={name}>{name}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
              <button
                onClick={() => setUploadResult(null)}
                className="ml-4 text-gray-400 hover:text-gray-600 text-lg leading-none"
                aria-label="Dismiss"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        <div className="flex justify-between items-start mb-8 flex-wrap gap-4">
          <div>
            {!isEditingInfo ? (
              <>
                <h1 className="text-3xl font-bold text-gray-900">{cube.name}</h1>
                {cube.description && <p className="text-gray-600 mt-2">{cube.description}</p>}
                {cube.cubecobra_link && (
                  <a
                    href={cube.cubecobra_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-indigo-600 hover:text-indigo-800 hover:underline mt-1 inline-flex items-center gap-1"
                  >
                    🔗 CubeCobra page
                  </a>
                )}
                <p className="text-sm text-gray-500 mt-1">
                  Total cards: {cubeSize?.total_cards || 0}
                </p>
                {isOwner && (
                  <button
                    onClick={() => {
                      setEditName(cube.name)
                      setEditDescription(cube.description ?? '')
                      setEditCubecobraLink(cube.cubecobra_link ?? '')
                      setIsEditingInfo(true)
                    }}
                    className="mt-2 text-sm text-gray-500 hover:text-gray-700 underline"
                  >
                    ✏️ Edit cube info
                  </button>
                )}
              </>
            ) : (
              <div className="space-y-3 w-80">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Cube Name</label>
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                  <textarea
                    rows={3}
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    placeholder="Describe your cube..."
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">CubeCobra Link (optional)</label>
                  <input
                    value={editCubecobraLink}
                    onChange={(e) => setEditCubecobraLink(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    placeholder="https://cubecobra.com/cube/overview/..."
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => updateInfoMutation.mutate()}
                    disabled={!editName.trim() || updateInfoMutation.isPending}
                    className="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {updateInfoMutation.isPending ? 'Saving…' : 'Save'}
                  </button>
                  <button
                    onClick={() => setIsEditingInfo(false)}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
          <div className="flex space-x-2 flex-wrap gap-2">
            <Link
              to={`/cubes/${cubeId}/drafts`}
              className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700"
            >
              Drafts
            </Link>
            <button
              onClick={() => setIsAddingCards(!isAddingCards)}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
            >
              {isAddingCards ? 'Cancel' : 'Update Cards'}
            </button>
            <button
              onClick={handleClearCards}
              disabled={!cubeCards || cubeCards.length === 0}
              className="bg-yellow-600 text-white px-4 py-2 rounded-md hover:bg-yellow-700 disabled:bg-gray-400"
            >
              Clear All Cards
            </button>
            <button
              onClick={handleDelete}
              className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>

        {/* ── Cube Settings panel (owner only) ── */}
        {isOwner && (
          <div className="bg-white rounded-lg shadow-md border border-gray-100 mb-4">
            <button
              type="button"
              onClick={() => setShowSettings((v) => !v)}
              className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
            >
              <span className="font-semibold text-gray-800">⚙️ Cube Settings</span>
              <span className="text-gray-400 text-sm">{showSettings ? '▲ Hide' : '▼ Show'}</span>
            </button>

            {showSettings && (
              <div className="border-t border-gray-100 px-5 py-5 space-y-4">
                <p className="text-sm text-gray-500">These settings are shown to players when they join a hosted event for this cube.</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Starting Life Total</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={settingsLifeTotal}
                      onChange={(e) => setSettingsLifeTotal(parseInt(e.target.value) || 20)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Packs per Player</label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={settingsPackCount}
                      onChange={(e) => setSettingsPackCount(parseInt(e.target.value) || 3)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cards per Pack</label>
                    <input
                      type="number"
                      min={1}
                      max={30}
                      value={settingsPackSize}
                      onChange={(e) => setSettingsPackSize(parseInt(e.target.value) || 15)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Draft Rules</label>
                  <textarea
                    rows={3}
                    value={settingsDraftRules}
                    onChange={(e) => setSettingsDraftRules(e.target.value)}
                    placeholder="e.g. Rochester draft, rotate packs clockwise, any custom rules..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Gameplay Rules</label>
                  <textarea
                    rows={3}
                    value={settingsGameplayRules}
                    onChange={(e) => setSettingsGameplayRules(e.target.value)}
                    placeholder="e.g. No sticker sheets, banned cards, alternate win conditions..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex justify-end gap-3">
                  {updateSettingsMutation.isError && (
                    <p className="text-sm text-red-600 self-center">Error saving settings.</p>
                  )}
                  <button
                    type="button"
                    onClick={() => setShowSettings(false)}
                    className="px-4 py-2 rounded-md border border-gray-300 text-sm text-gray-600 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => updateSettingsMutation.mutate()}
                    disabled={updateSettingsMutation.isPending}
                    className="px-6 py-2 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-50"
                  >
                    {updateSettingsMutation.isPending ? 'Saving...' : 'Save Settings'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {isAddingCards && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Update Cards</h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => setIsBulkUpload(false)}
                  className={`px-4 py-2 rounded ${
                    !isBulkUpload
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Search
                </button>
                <button
                  onClick={() => setIsBulkUpload(true)}
                  className={`px-4 py-2 rounded ${
                    isBulkUpload
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Bulk Upload
                </button>
              </div>
            </div>

            {isBulkUpload ? (
              <div>
                <p className="text-sm text-gray-600 mb-2">
                  Paste your card list below (one card per line):
                </p>
                <textarea
                  value={bulkCardList}
                  onChange={(e) => setBulkCardList(e.target.value)}
                  placeholder={'Lightning Bolt\nCounterspell\nSwords to Plowshares\n...'}
                  rows={10}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm mb-4"
                />
                <button
                  onClick={handleBulkUpload}
                  disabled={isProcessingBulk}
                  className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-400"
                >
                  {isProcessingBulk ? 'Processing...' : 'Add All Cards'}
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Replace Card banner — shown when both sides are staged */}
                {stagedAddCard && stagedRemoveCard && (
                  <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3">
                    <div className="flex-1 text-sm">
                      <span className="font-medium text-gray-600">Replace </span>
                      <span className="font-semibold text-red-600">{stagedRemoveCard.card?.name}</span>
                      <span className="text-gray-400 mx-2">→</span>
                      <span className="font-semibold text-green-600">{stagedAddCard.name}</span>
                    </div>
                    <button
                      onClick={handleReplaceCard}
                      disabled={isReplacing}
                      className="bg-indigo-600 text-white px-4 py-1.5 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
                    >
                      {isReplacing ? 'Replacing...' : 'Replace Card'}
                    </button>
                    <button
                      onClick={() => { setStagedAddCard(null); setStagedRemoveCard(null) }}
                      className="text-gray-400 hover:text-gray-600 text-lg leading-none"
                    >
                      ✕
                    </button>
                  </div>
                )}

                {/* ── Add a Card ── */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Add a Card</h3>
                  <div className="flex space-x-2 mb-3">
                    <input
                      type="text"
                      value={addSearchText}
                      onChange={(e) => setAddSearchText(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddSearch()}
                      placeholder="Search Scryfall..."
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={handleAddSearch}
                      className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                    >
                      Search
                    </button>
                  </div>
                  {addResults.length > 0 && (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {addResults.map((card: any) => (
                        <div
                          key={card.id}
                          className={`border rounded-lg p-2 cursor-pointer transition-all ${
                            stagedAddCard?.id === card.id
                              ? 'border-green-500 ring-2 ring-green-300 bg-green-50'
                              : 'border-gray-200 hover:border-gray-400'
                          }`}
                          onClick={() => setStagedAddCard(stagedAddCard?.id === card.id ? null : card)}
                        >
                          {card.small_image_url && (
                            <img src={card.small_image_url} alt={card.name} className="w-full rounded mb-1" />
                          )}
                          <p className="text-xs font-semibold truncate">{card.name}</p>
                          <p className="text-xs text-gray-500 truncate mb-1">{card.type_line}</p>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleAddCard(card) }}
                            className="w-full bg-green-600 text-white text-xs py-1 rounded hover:bg-green-700"
                          >
                            Add to Cube
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* ── Remove a Card ── */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Remove a Card</h3>
                  <input
                    type="text"
                    value={removeSearchText}
                    onChange={(e) => setRemoveSearchText(e.target.value)}
                    placeholder="Filter cards in cube by name..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-400 mb-3"
                  />
                  {removeSearchText.trim() && (() => {
                    const matches = (cubeCards ?? [])
                      .filter((cc) => cc.card?.name.toLowerCase().includes(removeSearchText.toLowerCase()))
                      .slice(0, 12)
                    return matches.length > 0 ? (
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                        {matches.map((cc) => (
                          <div
                            key={cc.id}
                            className={`border rounded-lg p-2 cursor-pointer transition-all ${
                              stagedRemoveCard?.id === cc.id
                                ? 'border-red-500 ring-2 ring-red-300 bg-red-50'
                                : 'border-gray-200 hover:border-gray-400'
                            }`}
                            onClick={() => setStagedRemoveCard(stagedRemoveCard?.id === cc.id ? null : cc)}
                          >
                            {cc.card?.small_image_url && (
                              <img src={cc.card.small_image_url} alt={cc.card?.name} className="w-full rounded mb-1" />
                            )}
                            <p className="text-xs font-semibold truncate">{cc.card?.name}</p>
                            <p className="text-xs text-gray-500 mb-1">{cc.quantity}× in cube</p>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleDecrementCard(cc) }}
                              className="w-full bg-red-600 text-white text-xs py-1 rounded hover:bg-red-700"
                            >
                              Remove 1
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500">No cards match "{removeSearchText}"</p>
                    )
                  })()}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-md">
          {/* ── Tab bar ── */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('cards')}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'cards'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Card List
            </button>
            <button
              onClick={() => setActiveTab('stats')}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'stats'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              📊 Statistics
            </button>
          </div>

          <div className="p-6">
          {activeTab === 'stats' ? (
            <CubeStatsPanel cubeId={cubeId} />
          ) : cardsLoading ? (
            <p className="text-gray-600">Loading cards...</p>
          ) : cubeCards && cubeCards.length > 0 ? (() => {
            const { byType, byCombo } = organizeCards(cubeCards.filter((c) => c.card))

            // Reusable card row renderer
            const renderCardRow = (cubeCard: CubeCardList[number], keyStr?: string) => (
              <div
                key={keyStr ?? cubeCard.id}
                className="group relative flex items-center justify-between rounded px-1 py-0.5 hover:bg-white hover:shadow-sm"
                onMouseEnter={(e) => handleCardMouseEnter(cubeCard.card?.image_url, e)}
                onMouseMove={handleCardMouseMove}
                onMouseLeave={handleCardMouseLeave}
              >
                <Link
                  to={`/cards/${cubeCard.card_id}?cubeId=${cubeId}`}
                  className="text-xs text-blue-700 hover:text-blue-900 hover:underline truncate flex-1 leading-tight"
                >
                  {cubeCard.card?.name}
                </Link>
                <button
                  onClick={async () => {
                    await cubesApi.decrementCardFromCube(cubeId, cubeCard.card_id)
                    queryClient.invalidateQueries({ queryKey: ['cubeCards', cubeId] })
                    queryClient.invalidateQueries({ queryKey: ['cubeSize', cubeId] })
                  }}
                  className="hidden group-hover:block ml-1 shrink-0 text-red-500 hover:text-red-700 text-xs leading-none"
                  title="Remove 1"
                >
                  ✕
                </button>
              </div>
            )

            // Renders a sorted card list with a thin divider whenever CMC changes.
            // Cards with quantity > 1 are rendered as that many individual rows.
            const renderWithCmcDividers = (cards: CubeCardList) => {
              const rows: React.ReactNode[] = []
              let lastCmc: number | undefined = undefined
              let rowIndex = 0
              cards.forEach((c, i) => {
                const cmc = c.card?.cmc ?? 0
                const qty = c.quantity ?? 1
                if (i > 0 && cmc !== lastCmc)
                  rows.push(<div key={`cmc-div-${i}`} className="border-t border-gray-300 my-0.5" />)
                for (let q = 0; q < qty; q++) {
                  rows.push(renderCardRow(c, `${c.id}-${rowIndex++}`))
                }
                lastCmc = cmc
              })
              return rows
            }

            return (
              <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${COLORS.filter((color) => { const isCombo = color === 'Multicolored' || color === 'Lands'; const comboCol = byCombo[color as 'Multicolored' | 'Lands']; const typeCol = byType[color as MonoColorKey]; const total = isCombo ? Object.values(comboCol).reduce((n, arr) => n + arr.length, 0) : TYPE_ORDER.reduce((n, t) => n + typeCol[t].length, 0); return total > 0; }).length}, minmax(0, 1fr))` }}>
                  {COLORS.map((color) => {
                    const isCombo = color === 'Multicolored' || color === 'Lands'
                    const comboCol = byCombo[color as 'Multicolored' | 'Lands']
                    const typeCol  = byType[color as MonoColorKey]
                    const colTotal = isCombo
                      ? Object.values(comboCol).reduce((n, arr) => n + arr.reduce((s, cc) => s + (cc.quantity ?? 1), 0), 0)
                      : TYPE_ORDER.reduce((n, t) => n + typeCol[t].reduce((s, cc) => s + (cc.quantity ?? 1), 0), 0)
                    if (colTotal === 0) return null
                    return (
                      <div key={color} className={`rounded-lg border ${COLOR_STYLES[color]} p-2 overflow-y-auto max-h-[72vh]`}>
                        <div className="text-center font-bold text-sm mb-2 border-b border-current pb-1">
                          {color} <span className="font-normal text-gray-500">({colTotal})</span>
                        </div>

                        {isCombo ? (() => {
                          // Multicolored & Lands: group by color-combination in WUBRG order
                          let renderedCombo = 0
                          return ALL_COLOR_GROUPS.map((group) => {
                            const cards = comboCol[group]
                            if (!cards || cards.length === 0) return null
                            const label = group === 'C' ? 'Colorless' : group
                            const needsDivider = renderedCombo++ > 0
                            return (
                              <div key={group} className={needsDivider ? 'mt-1 pt-1 border-t-2 border-gray-400' : ''}>
                                <div className="text-xs font-semibold text-gray-500 mb-1">
                                  {label} ({cards.reduce((s, cc) => s + (cc.quantity ?? 1), 0)})
                                </div>
                                <div>
                                  {renderWithCmcDividers(cards)}
                                </div>
                              </div>
                            )
                          })
                        })() : (() => {
                          // Mono-color / Colorless: group by card type
                          let renderedType = 0
                          return TYPE_ORDER.map((type) => {
                            const cards = typeCol[type]
                            if (cards.length === 0) return null
                            const needsDivider = renderedType++ > 0
                            return (
                              <div key={type} className={needsDivider ? 'mt-1 pt-1 border-t-2 border-gray-400' : ''}>
                                <div className="text-xs font-semibold text-gray-500 mb-1">
                                  {type} ({cards.reduce((s, cc) => s + (cc.quantity ?? 1), 0)})
                                </div>
                                <div>
                                  {renderWithCmcDividers(cards)}
                                </div>
                              </div>
                            )
                          })
                        })()}
                      </div>
                    )
                  })}
              </div>
            )
          })() : (
            <p className="text-gray-600">
              No cards in this cube yet. Click "Add Cards" to get started.
            </p>
          )}
          </div>{/* end p-6 inner wrapper */}
        </div>
      </div>

      {/* Card image tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none rounded-lg shadow-2xl border border-gray-300 overflow-hidden"
          style={{
            left: tooltip.x + 16,
            top: tooltip.y - 60,
            transform: tooltip.x > window.innerWidth - 240 ? 'translateX(calc(-100% - 32px))' : undefined,
          }}
        >
          <img src={tooltip.imageUrl} alt="" className="w-48" />
        </div>
      )}
    </Layout>
  )
}
