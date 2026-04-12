"""
Demo seed script — creates a fully-populated test environment.

Creates:
  • One demo user  (email: demo@cube.test / password: demopass123)
  • One cube with every card on the provided list (fetched from Scryfall)
  • 4 fictional fake-player accounts used as opponents
  • 5 draft events with 6 players each, deck lists, wins/losses,
    AI-generated descriptions + archetype tags, card feedback,
    post-draft feedback, and a draft AI narrative.

Run from the back_end directory with the venv active:
    python seed_demo.py

Re-running is safe — it skips already-existing data wherever possible.
"""
import sys
import os
import json
import random
import time
import logging

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("seed")

# ---------------------------------------------------------------------------
# DB / service imports (after path + env setup)
# ---------------------------------------------------------------------------
from database import SessionLocal, Base, engine
from api.models import (
    User, Cube, CubeCard, DraftEvent, DraftParticipant,
    UserDeck, Feedback, CardFeedback, PostDraftFeedback, Card,
    DraftRound, DraftPairing, DraftSeat,
)
from api.services import (
    UserService, CardService, ScryfallService, CubeStatsService, AIService
)
from api.services.user_deck_service import UserDeckService
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Cube list
# ---------------------------------------------------------------------------
CUBE_CARDS = [
    "Guide of Souls","Hopeful Initiate","Mikaeus, the Lunarch","Skrelv, Defector Mite",
    "Anafenza, Kin-Tree Spirit","Dusk Legion Duelist","Grateful Apparition","Lion Sash",
    "Luminarch Aspirant","Metastatic Evangel","Reluctant Role Model","Scholar of New Horizons",
    "Suncleanser","Anafenza, Unyielding Lineage","Angelic Sleuth","Annex Sentry",
    "Kutzil's Flanker","Lae'zel, Vlaakith's Champion","Patrolling Peacemaker","Proud Pack-Rhino",
    "Rosie Cotton of South Lane","Summon: Ixion","Basri's Lieutenant","Emiel the Blessed",
    "Filigree Vector","Priest of the Crossing","Salvation Swan","General Leo Cristophe",
    "Skyboon Evangelist","Sanctuary Warden","Ajani Steadfast","The Wandering Emperor",
    "Elspeth Resplendent","Get Lost","Parting Gust","Unbounded Potential","Jolted Awake",
    "Requisition Raid","Wrath of the Skies","Sunfall","Staff of the Storyteller",
    "Static Prison","Swift Reconfiguration","Out of Time","Resourceful Defense",
    "Touch the Spirit Realm","Crack in Time","Elspeth Conquers Death","Virtue of Loyalty",
    "Benthic Biomancer","Elusive Otter","Ingenious Prodigy","Aven Courier","Flesh Duplicate",
    "Jace, Vryn's Prodigy","Ledger Shredder","Mercurial Spelldancer","Spectral Adversary",
    "Thrummingbird","Dreamtide Whale","Flux Channeler","Glen Elendra Guardian","Referee Squad",
    "Danny Pink","Glen Elendra Archmage","Tekuthal, Inquiry Dominus","Twenty-Toed Toad",
    "Viral Drake","Deekah, Fractal Theorist","Deepglow Skate","Mirelurk Queen","Shield Broker",
    "Jace, Architect of Thought","Jace, the Mind Sculptor","Teferi, Temporal Pilgrim",
    "Tune the Narrative","Aether Spike","Counterspell","Essence Capture","Experimental Augury",
    "Mana Leak","Ripples of Potential","Serum Snare","Teferi's Time Twist","Reject Imperfection",
    "Saruman's Trickery","Radstorm","Storm of Forms","Wicked Slumber","Intrude on the Mind",
    "Commence the Endgame","Clutch of Currents","Callous Dismissal","Part the Waterveil",
    "Ichormoon Gauntlet","Proft's Eidetic Memory","Carrion Feeder","Stalactite Stalker",
    "Thrull Parasite","Blightbelly Rat","Orcish Bowmasters","Putrid Goblin","Vampire Hexmage",
    "Banewhip Punisher","Flesh Carver","Mutated Cultist","Necroskitter","Spitting Dilophosaurus",
    "Urborg Scavengers","Woe Strider","Body Launderer","Massacre Girl, Known Killer",
    "Siegfried, Famed Swordsman","Skinrender","Yawgmoth, Thran Physician",
    "Kinzu of the Bleak Coven","Puppeteer Clique","Blight Titan","Mikaeus, the Unhallowed",
    "Thief of Blood","Liliana of the Veil","Liliana, Death's Majesty","Vraska, Betrayal's Sting",
    "Requiting Hex","Wither and Bloom","Grim Affliction","Lethal Scheme","Makeshift Mannequin",
    "Contagion","Lethal Throwdown","Black Sun's Zenith","Dai Li Indoctrination","Drown in Ichor",
    "Nuclear Fallout","Traumatic Revelation","Ruinous Path","Gix's Command","Dreadhorde Invasion",
    "Glistening Oil","Blowfly Infestation","Elspeth's Nightmare","Nest of Scarabs",
    "Out of the Tombs","The Cruelty of Gix","Cacophony Scamp","Sawblade Scamp",
    "Shivan Devastator","Akki Ember-Keeper","Amped Raptor","Bloodthirsty Adversary",
    "Flametongue Yearling","Goro-Goro, Disciple of Ryusei","Ian the Reckless",
    "Inti, Seneschal of the Sun","Molten Hydra","Runaway Steam-Kin","Smoldering Egg",
    "Upriser Renegade","Exocrine","Gleeful Arsonist","Krenko, Tin Street Kingpin",
    "Legion Warboss","Voldaren Thrillseeker","Redcap Gutter-Dweller","Thundering Raiju",
    "Kami of Celebration","Akki Battle Squad","Overlord of the Boilerbilges",
    "Territorial Aetherkite","Chandra, Acolyte of Flame","Chandra, Pyromaster",
    "Chandra, Hope's Beacon","Flame Discharge","Galvanic Discharge","Abrade","Kami's Flare",
    "Puncture Bolt","Puncture Blast","Volt Charge","Flame Slash","Light Up the Night",
    "Reiterating Bolt","Honor the God-Pharaoh","Mark of Mutiny","Chainsaw",
    "Shrine of Burning Rage","Curse of Stalked Prey","Ordeal of Purphoros","Ion Storm",
    "The Flux","Deathbonnet Sprout","District Mascot","Jadelight Spelunker","Joraga Treespeaker",
    "Young Wolf","Basking Broodscale","Blanchwood Prowler","Cankerbloom","Cathedral Acolyte",
    "Devoted Druid","Obsessive Skinner","Pollenbright Druid","Questing Druid","Scavenging Ooze",
    "Strangleroot Geist","Twitching Doll","Arwen, Weaver of Hope","Bloated Contaminator",
    "Evolution Sage","Evolution Witness","Generous Patron","Kodama of the West Tree",
    "Park Heights Maverick","Peema Trailblazer","Scurry Oak","Tireless Tracker",
    "Watchful Radstag","Bannerhide Krushok","Slippery Bogbonder","Tributary Instructor",
    "Wickerbough Elder","Contaminant Grafter","Golgari Grave-Troll","Verdurous Gearhulk",
    "Quilled Greatwurm","Ferrafor, Young Yew","Woodfall Primus","Garruk Wildspeaker",
    "Vivien Reid","Vivien, Monsters' Advocate","Infectious Bite","Inscription of Abundance",
    "Smell Fear","Carnivorous Canopy","Ozolith, the Shattered Spire","Hardened Scales",
    "Innkeeper's Talent","Teachings of the Kirin","Curse of Predation","Doubling Season",
    "Hangarback Walker","Walking Ballista","Hex Parasite","Lore Seeker",
    "Clay Golem","Cogwork Librarian","Crystalline Crawler","Triskelion","Tezzeret's Gambit",
    "Engineered Explosives","Everflowing Chalice","Animation Module","Luxior, Giada's Gift",
    "Tarrian's Soulcleaver","Contagion Clasp","Moxite Refinery","Noble's Purse",
    "Power Conduit","Reckoner Bankbuster","Solar Transformer","The Filigree Sylex",
    "Aetheric Amplifier","Glistening Sphere","Staff of Compleation","Recon Craft Theta",
    "Contagion Engine","Celestial Regulator","Dovin, Grand Arbiter","Soulherder",
    "Denry Klin, Editor in Chief","Oath of Teferi","Soul Diviner","Venser, Corpse Puppet",
    "Kaito Shizuki","Kaito, Dancing Shadow","Juri, Master of the Revue",
    "Alesha, Who Laughs at Fate","Murderous Redcap","The Scorpion God","Deathbringer Thoctar",
    "Mawloc","Grumgully, the Generous","Halana and Alena, Partners","Lukka, Bound to Ruin",
    "Dromoka's Command","Arwen, Mortal Queen","Kitchen Finks","Ajani, Sleeper Agent",
    "Sovereign Okinec Ahau","Feast of the Victorious Dead","Elenda, the Dusk Rose",
    "Felisa, Fang of Silverquill","Sorin, Vengeful Bloodlord","Dack's Duplicate",
    "Battle of Frost and Fire","Ral, Izzet Viceroy","Winged Hive Tyrant",
    "Hapatra, Vizier of Poisons","Lotleth Troll","Varolz, the Scar-Striped","Atomize",
    "Anim Pakal, Thousandth Moon","Jenny, Generated Anomaly","Nahiri, the Harbinger",
    "Assemble the Legion","Repulsive Mutation","Tainted Observer","Dreamdew Entrancer",
    "Ezuri, Stalker of Spheres","Zimone, Paradox Sculptor","Falco Spara, Pactweaver",
    "Raffine, Scheming Seer","Saruman, the White Hand","Bright-Palm, Soul Awakener",
    "Cayth, Famed Mechanist","Indominus Rex, Alpha","Volrath, the Shapestealer",
    "Atraxa, Praetors' Voice","Glacial Fortress","Hallowed Fountain","Restless Anchorage",
    "Creeping Tar Pit","Drowned Catacomb","Watery Grave","Blood Crypt","Dragonskull Summit",
    "Lavaclaw Reaches","Raging Ravine","Rootbound Crag","Stomping Ground","Restless Prairie",
    "Sunpetal Grove","Temple Garden","Godless Shrine","Isolated Chapel","Shambling Vent",
    "Steam Vents","Sulfur Falls","Wandering Fumarole","Hissing Quagmire","Overgrown Tomb",
    "Woodland Cemetery","Clifftop Retreat","Restless Bivouac","Sacred Foundry","Breeding Pool",
    "Hinterland Harbor","Lumbering Falls","Spara's Headquarters","Raffine's Tower",
    "Xander's Lounge","Ziatora's Proving Ground","Jetmir's Garden","Savai Triome",
    "Ketria Triome","Indatha Triome","Raugrin Triome","Zagoth Triome","Arid Mesa",
    "Bloodstained Mire","Crawling Barrens","Fabled Passage","Field of Ruin",
    "Flooded Strand","Gemstone Mine","Karn's Bastion","Mana Confluence","Marsh Flats",
    "Misty Rainforest","Nesting Grounds","Polluted Delta","Prismatic Vista","Scalding Tarn",
    "Verdant Catacombs","Vivid Crag","Vivid Creek","Vivid Grove","Vivid Marsh","Vivid Meadow",
    "Windswept Heath","Wooded Foothills",
]

# ---------------------------------------------------------------------------
# Fake players and draft scenarios
# ---------------------------------------------------------------------------
FAKE_PLAYERS = [
    {"username": "aggro_alex",   "email": "alex@cube.test",    "password": "fakepass1"},
    {"username": "control_carl", "email": "carl@cube.test",    "password": "fakepass2"},
    {"username": "midrange_mia", "email": "mia@cube.test",     "password": "fakepass3"},
    {"username": "combo_ben",    "email": "ben@cube.test",     "password": "fakepass4"},
    {"username": "tempo_tara",   "email": "tara@cube.test",    "password": "fakepass5"},
]

# 5 draft events. Each has 6 slots (demo owner + 5 fake players).
# deck_cards is a list of indicies into the cube card list.
# We'll resolve to actual card IDs after loading the cube.
# Records are (wins, losses).
DRAFT_SCENARIOS = [
    {
        "name": "Peasant Cube Draft #1",
        "date_offset_days": -45,
        "decks": [
            {
                "player": "demo",
                "deck_name": "WB Counters Beatdown",
                "archetype": "aggro",
                "archetype_detail": "white black counters",
                "colors": ["W", "B"],
                "card_names": [
                    "Guide of Souls","Hopeful Initiate","Luminarch Aspirant","Anafenza, Kin-Tree Spirit",
                    "Lion Sash","Dusk Legion Duelist","Lae'zel, Vlaakith's Champion","Basri's Lieutenant",
                    "Grateful Apparition","Sanctuary Warden","Ajani Steadfast","The Wandering Emperor",
                    "Carrion Feeder","Vampire Hexmage","Woe Strider","Feast of the Victorious Dead",
                    "Elenda, the Dusk Rose","Sorin, Vengeful Bloodlord","Ajani, Sleeper Agent",
                    "Arwen, Mortal Queen","Godless Shrine","Isolated Chapel","Shambling Vent",
                ],
                "wins": 3, "losses": 0,
                "feedback_comment": "Counters synergy was incredible! Ajani + Luminarch Aspirant felt unfair.",
                "feedback_rating": 5,
            },
            {
                "player": "aggro_alex",
                "deck_name": "RG Stompy",
                "archetype": "aggro",
                "archetype_detail": "red green stompy",
                "colors": ["R", "G"],
                "card_names": [
                    "Cacophony Scamp","Sawblade Scamp","Bloodthirsty Adversary","Runaway Steam-Kin",
                    "Gleeful Arsonist","Inti, Seneschal of the Sun","Amped Raptor","Smoldering Egg",
                    "Halana and Alena, Partners","Legion Warboss","Voldaren Thrillseeker",
                    "Strangleroot Geist","Young Wolf","Evolution Witness","Scavenging Ooze",
                    "Bloated Contaminator","Volt Charge","Abrade","Raging Ravine","Stomping Ground",
                    "Rootbound Crag","Wooded Foothills","Bloodstained Mire",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "Felt good but the counters deck was too fast out of the gate.",
                "feedback_rating": 4,
            },
            {
                "player": "control_carl",
                "deck_name": "UB Proliferate Control",
                "archetype": "control",
                "archetype_detail": "blue black proliferate",
                "colors": ["U", "B"],
                "card_names": [
                    "Thrummingbird","Flux Channeler","Viral Drake","Tekuthal, Inquiry Dominus",
                    "Deepglow Skate","Jace, the Mind Sculptor","Teferi, Temporal Pilgrim",
                    "Ichormoon Gauntlet","Proft's Eidetic Memory","Counterspell","Mana Leak",
                    "Serum Snare","Grim Affliction","Drown in Ichor","Vraska, Betrayal's Sting",
                    "Liliana of the Veil","Yawgmoth, Thran Physician","Black Sun's Zenith",
                    "Creeping Tar Pit","Watery Grave","Drowned Catacomb","Polluted Delta",
                    "Contagion Clasp",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "Proliferate felt very powerful. Yawgmoth is probably too good.",
                "feedback_rating": 4,
            },
            {
                "player": "midrange_mia",
                "deck_name": "BG Counters Value",
                "archetype": "midrange",
                "archetype_detail": "golgari counters value",
                "colors": ["B", "G"],
                "card_names": [
                    "Deathbonnet Sprout","Cankerbloom","Obsessive Skinner","Evolution Sage",
                    "Bloated Contaminator","Scavenging Ooze","Tireless Tracker","Varolz, the Scar-Striped",
                    "Hapatra, Vizier of Poisons","Yawgmoth, Thran Physician","Woe Strider",
                    "Wither and Bloom","Smell Fear","Carnivorous Canopy","Contagion Clasp",
                    "Hardened Scales","Walking Ballista","Ozolith, the Shattered Spire",
                    "Overgrown Tomb","Hissing Quagmire","Woodland Cemetery","Verdant Catacombs",
                    "Zagoth Triome",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "Golgari felt solid but the aggro decks were too fast.",
                "feedback_rating": 3,
            },
            {
                "player": "combo_ben",
                "deck_name": "UR Spells Tempo",
                "archetype": "combo",
                "archetype_detail": "spellslinger",
                "colors": ["U", "R"],
                "card_names": [
                    "Mercurial Spelldancer","Ledger Shredder","Bloodthirsty Adversary",
                    "Runaway Steam-Kin","Flux Channeler","Jace, Vryn's Prodigy","Danny Pink",
                    "Chandra, Acolyte of Flame","Counterspell","Mana Leak","Experimental Augury",
                    "Aether Spike","Tune the Narrative","Ripples of Potential","Serum Snare",
                    "Volt Charge","Galvanic Discharge","Ral, Izzet Viceroy","Steam Vents",
                    "Sulfur Falls","Wandering Fumarole","Scalding Tarn","Raugrin Triome",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "Spells plan was fun but hard to assemble critical mass.",
                "feedback_rating": 3,
            },
            {
                "player": "tempo_tara",
                "deck_name": "WU Blink Fliers",
                "archetype": "control",
                "archetype_detail": "azorius blink",
                "colors": ["W", "U"],
                "card_names": [
                    "Angelic Sleuth","Annex Sentry","Salvation Swan","Soulherder",
                    "Emiel the Blessed","Filigree Vector","Denry Klin, Editor in Chief",
                    "Aven Courier","Spectral Adversary","Flesh Duplicate","Ledger Shredder",
                    "Dovin, Grand Arbiter","Oath of Teferi","Touch the Spirit Realm",
                    "Parting Gust","Swift Reconfiguration","Out of Time","Counterspell",
                    "Hallowed Fountain","Glacial Fortress","Restless Anchorage","Flooded Strand",
                    "Spara's Headquarters",
                ],
                "wins": 0, "losses": 3,
                "feedback_comment": "Blink was underpowered, missing payoffs. Might need more value ETBs.",
                "feedback_rating": 2,
            },
        ],
    },
    {
        "name": "Peasant Cube Draft #2",
        "date_offset_days": -30,
        "decks": [
            {
                "player": "demo",
                "deck_name": "BR Aristocrats",
                "archetype": "combo",
                "archetype_detail": "aristocrats",
                "colors": ["B", "R"],
                "card_names": [
                    "Carrion Feeder","Woe Strider","Juri, Master of the Revue","Murderous Redcap",
                    "Gleeful Arsonist","Voldaren Thrillseeker","Elenda, the Dusk Rose",
                    "Kinzu of the Bleak Coven","Alesha, Who Laughs at Fate","The Scorpion God",
                    "Deathbringer Thoctar","Dreadhorde Invasion","Gix's Command","Lethal Scheme",
                    "Makeshift Mannequin","Ion Storm","Volt Charge","Mark of Mutiny",
                    "Blood Crypt","Dragonskull Summit","Lavaclaw Reaches","Bloodstained Mire",
                    "Xander's Lounge",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "Aristocrats came together beautifully. Juri is incredible in this shell.",
                "feedback_rating": 5,
            },
            {
                "player": "aggro_alex",
                "deck_name": "R Burn/Counters",
                "archetype": "aggro",
                "archetype_detail": "red burn",
                "colors": ["R"],
                "card_names": [
                    "Cacophony Scamp","Sawblade Scamp","Akki Ember-Keeper","Goro-Goro, Disciple of Ryusei",
                    "Ian the Reckless","Runaway Steam-Kin","Legion Warboss","Krenko, Tin Street Kingpin",
                    "Akki Battle Squad","Overlord of the Boilerbilges","Chandra, Pyromaster",
                    "Flame Discharge","Galvanic Discharge","Puncture Bolt","Volt Charge",
                    "Light Up the Night","Reiterating Bolt","Shrine of Burning Rage",
                    "Ordeal of Purphoros","Curse of Stalked Prey","Ion Storm","The Flux",
                    "Diamond City",
                ],
                "wins": 3, "losses": 0,
                "feedback_comment": "Mono red was absolutely oppressive. Felt like it was a tier above everything.",
                "feedback_rating": 3,
            },
            {
                "player": "control_carl",
                "deck_name": "UW Proliferate Walkers",
                "archetype": "control",
                "archetype_detail": "azorius superfriends",
                "colors": ["W", "U"],
                "card_names": [
                    "Thrummingbird","Flux Channeler","Deepglow Skate","Tekuthal, Inquiry Dominus",
                    "Oath of Teferi","Soul Diviner","Dovin, Grand Arbiter","Ajani Steadfast",
                    "The Wandering Emperor","Elspeth Resplendent","Jace, the Mind Sculptor",
                    "Teferi, Temporal Pilgrim","Ichormoon Gauntlet","Counterspell","Mana Leak",
                    "Serum Snare","Out of Time","Swift Reconfiguration","Hallowed Fountain",
                    "Glacial Fortress","Restless Anchorage","Flooded Strand","Spara's Headquarters",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "Superfriends with proliferate is insane value. Deepglow Skate wins on the spot.",
                "feedback_rating": 4,
            },
            {
                "player": "midrange_mia",
                "deck_name": "GW Counters Go-Wide",
                "archetype": "midrange",
                "archetype_detail": "selesnya counters",
                "colors": ["W", "G"],
                "card_names": [
                    "Anafenza, Kin-Tree Spirit","Luminarch Aspirant","Emiel the Blessed",
                    "Rosie Cotton of South Lane","Basri's Lieutenant","Sanctuary Warden",
                    "Evolution Sage","Kodama of the West Tree","Bloated Contaminator",
                    "Hardened Scales","Doubling Season","Ozolith, the Shattered Spire",
                    "Walking Ballista","Verdurous Gearhulk","Vivien, Monsters' Advocate",
                    "Inscription of Abundance","Dromoka's Command","Ajani, Sleeper Agent",
                    "Temple Garden","Sunpetal Grove","Restless Prairie","Windswept Heath",
                    "Jetmir's Garden",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "GW was powerful but just couldn't race mono red.",
                "feedback_rating": 4,
            },
            {
                "player": "combo_ben",
                "deck_name": "BG Infect",
                "archetype": "combo",
                "archetype_detail": "infect",
                "colors": ["B", "G"],
                "card_names": [
                    "Blightbelly Rat","Blanchwood Prowler","Bloated Contaminator","Cankerbloom",
                    "Glistening Oil","Necroskitter","Mutated Cultist","Viral Drake","Thrummingbird",
                    "Grim Affliction","Wither and Bloom","Drown in Ichor","Contagion Clasp",
                    "Contagion Engine","Carnivorous Canopy","Smell Fear","Walking Ballista",
                    "Ozolith, the Shattered Spire","Overgrown Tomb","Hissing Quagmire",
                    "Woodland Cemetery","Verdant Catacombs","Zagoth Triome",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "Infect was consistent but the lack of pump spells hurt.",
                "feedback_rating": 3,
            },
            {
                "player": "tempo_tara",
                "deck_name": "UB Tempo Fliers",
                "archetype": "midrange",
                "archetype_detail": "dimir tempo",
                "colors": ["U", "B"],
                "card_names": [
                    "Stalactite Stalker","Ledger Shredder","Spectral Adversary","Mercurial Spelldancer",
                    "Bodyguard","Aven Courier","Danny Pink","Jace, Vryn's Prodigy","Flesh Duplicate",
                    "Orcish Bowmasters","Flesh Carver","Woe Strider","Counterspell","Mana Leak",
                    "Serum Snare","Saruman's Trickery","Drown in Ichor","Makeshift Mannequin",
                    "Creeping Tar Pit","Watery Grave","Drowned Catacomb","Polluted Delta",
                    "Raffine's Tower",
                ],
                "wins": 0, "losses": 3,
                "feedback_comment": "Got crushed by mono red T1. The deck had no interaction at instant speed early.",
                "feedback_rating": 2,
            },
        ],
    },
    {
        "name": "Peasant Cube Draft #3",
        "date_offset_days": -18,
        "decks": [
            {
                "player": "demo",
                "deck_name": "UG Proliferate Ramp",
                "archetype": "combo",
                "archetype_detail": "simic proliferate ramp",
                "colors": ["U", "G"],
                "card_names": [
                    "Joraga Treespeaker","Devoted Druid","Benthic Biomancer","Thrummingbird",
                    "Flux Channeler","Evolution Sage","Kodama of the West Tree","Zimone, Paradox Sculptor",
                    "Ezuri, Stalker of Spheres","Deepglow Skate","Vivien Reid","Garruk Wildspeaker",
                    "Tezzeret's Gambit","Ripples of Potential","Tune the Narrative","Animation Module",
                    "Contagion Clasp","Contagion Engine","Breeding Pool","Hinterland Harbor",
                    "Lumbering Falls","Misty Rainforest","Ketria Triome",
                ],
                "wins": 3, "losses": 0,
                "feedback_comment": "Simic proliferate was oppressive. Ezuri + counters producers snowballed fast.",
                "feedback_rating": 5,
            },
            {
                "player": "aggro_alex",
                "deck_name": "WG Tokens",
                "archetype": "aggro",
                "archetype_detail": "selesnya tokens",
                "colors": ["W", "G"],
                "card_names": [
                    "Guide of Souls","Hopeful Initiate","Luminarch Aspirant","Anafenza, Kin-Tree Spirit",
                    "Emiel the Blessed","Scurry Oak","Rosie Cotton of South Lane","Basri's Lieutenant",
                    "Assemble the Legion","Anim Pakal, Thousandth Moon","Sovereign Okinec Ahau",
                    "Doubling Season","Vivien, Monsters' Advocate","Dromoka's Command",
                    "Inscription of Abundance","Ajani, Sleeper Agent","Walking Ballista",
                    "Hangarback Walker","Temple Garden","Sunpetal Grove","Restless Prairie",
                    "Windswept Heath","Jetmir's Garden",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "Tokens was explosive but simic ramp went over the top too easily.",
                "feedback_rating": 4,
            },
            {
                "player": "control_carl",
                "deck_name": "BW Reanimator",
                "archetype": "combo",
                "archetype_detail": "reanimator",
                "colors": ["W", "B"],
                "card_names": [
                    "Puppeteer Clique","Blight Titan","Mikaeus, the Unhallowed","Golgari Grave-Troll",
                    "Felisa, Fang of Silverquill","Sorin, Vengeful Bloodlord","Elenda, the Dusk Rose",
                    "Makeshift Mannequin","Out of the Tombs","Traumatic Revelation","Dai Li Indoctrination",
                    "Liliana, Death's Majesty","Wrath of the Skies","Sunfall","Elspeth Conquers Death",
                    "Virtue of Loyalty","Crack in Time","Sanctuary Warden","Godless Shrine",
                    "Isolated Chapel","Shambling Vent","Marsh Flats","Savai Triome",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "Reanimator was very fun. Blight Titan felt like a bomb.",
                "feedback_rating": 4,
            },
            {
                "player": "midrange_mia",
                "deck_name": "RG Counters Beats",
                "archetype": "midrange",
                "archetype_detail": "gruul counters",
                "colors": ["R", "G"],
                "card_names": [
                    "Grumgully, the Generous","Halana and Alena, Partners","Molten Hydra",
                    "Shivan Devastator","Territorial Aetherkite","Verdurous Gearhulk",
                    "Evolution Sage","Tireless Tracker","Park Heights Maverick","Bloated Contaminator",
                    "Hardened Scales","Ozolith, the Shattered Spire","Ion Storm","Volt Charge",
                    "Abrade","Kami's Flare","Chandra, Hope's Beacon","Vivien Reid",
                    "Raging Ravine","Stomping Ground","Rootbound Crag","Wooded Foothills",
                    "Ziatora's Proving Ground",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "Gruul felt a bit underpowered compared to the simic and token builds.",
                "feedback_rating": 3,
            },
            {
                "player": "combo_ben",
                "deck_name": "4-Color Superfriends",
                "archetype": "control",
                "archetype_detail": "4-color superfriends",
                "colors": ["W", "U", "B", "G"],
                "card_names": [
                    "Ajani Steadfast","The Wandering Emperor","Jace, the Mind Sculptor",
                    "Teferi, Temporal Pilgrim","Liliana of the Veil","Vraska, Betrayal's Sting",
                    "Vivien Reid","Garruk Wildspeaker","Deepglow Skate","Oath of Teferi",
                    "Doubling Season","Ichormoon Gauntlet","Thrummingbird","Flux Channeler",
                    "Counterspell","Serum Snare","Gix's Command","Contagion Engine",
                    "Mana Confluence","Gemstone Mine","Fabled Passage","Prismatic Vista",
                    "Atraxa, Praetors' Voice",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "4-colour greedy mana base was inconsistent but powerful when it worked.",
                "feedback_rating": 4,
            },
            {
                "player": "tempo_tara",
                "deck_name": "RB Sacrifice",
                "archetype": "combo",
                "archetype_detail": "rakdos sacrifice",
                "colors": ["B", "R"],
                "card_names": [
                    "Carrion Feeder","Woe Strider","Murderous Redcap","Juri, Master of the Revue",
                    "Alesha, Who Laughs at Fate","Deathbringer Thoctar","Kinzu of the Bleak Coven",
                    "Voldaren Thrillseeker","Dreadhorde Invasion","Gix's Command","Lethal Scheme",
                    "Ion Storm","Mark of Mutiny","Makeshift Mannequin","Nuclear Fallout",
                    "Ruinous Path","The Cruelty of Gix","Chandra, Acolyte of Flame",
                    "Blood Crypt","Dragonskull Summit","Lavaclaw Reaches","Bloodstained Mire",
                    "Xander's Lounge",
                ],
                "wins": 0, "losses": 3,
                "feedback_comment": "Sacrifice needed more redundancy. Lost to simic's size advantage.",
                "feedback_rating": 3,
            },
        ],
    },
    {
        "name": "Peasant Cube Draft #4",
        "date_offset_days": -10,
        "decks": [
            {
                "player": "demo",
                "deck_name": "WB Counters Midrange",
                "archetype": "midrange",
                "archetype_detail": "orzhov counters",
                "colors": ["W", "B"],
                "card_names": [
                    "Guide of Souls","Hopeful Initiate","Dusk Legion Duelist","Luminarch Aspirant",
                    "Lae'zel, Vlaakith's Champion","Anafenza, Kin-Tree Spirit","Anafenza, Unyielding Lineage",
                    "Sanctuary Warden","Feast of the Victorious Dead","Elenda, the Dusk Rose",
                    "Sorin, Vengeful Bloodlord","Ajani, Sleeper Agent","Arwen, Mortal Queen",
                    "Yawgmoth, Thran Physician","Woe Strider","Liliana of the Veil",
                    "Wrath of the Skies","Sunfall","Elspeth Conquers Death","Godless Shrine",
                    "Isolated Chapel","Shambling Vent","Marsh Flats",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "Another solid WB build. Yawgmoth carried hard.",
                "feedback_rating": 4,
            },
            {
                "player": "aggro_alex",
                "deck_name": "UR Artifacts",
                "archetype": "combo",
                "archetype_detail": "izzet artifacts",
                "colors": ["U", "R"],
                "card_names": [
                    "Hangarback Walker","Walking Ballista","Crystalline Crawler","Triskelion",
                    "Animation Module","Contagion Clasp","Everflowing Chalice","Engineered Explosives",
                    "Reckoner Bankbuster","The Filigree Sylex","Aetheric Amplifier","Glistening Sphere",
                    "Contagion Engine","Ledger Shredder","Mercurial Spelldancer","Flux Channeler",
                    "Chandra, Hope's Beacon","Ral, Izzet Viceroy","Steam Vents","Sulfur Falls",
                    "Wandering Fumarole","Scalding Tarn","Raugrin Triome",
                ],
                "wins": 3, "losses": 0,
                "feedback_comment": "Artifacts shell was unbeatable. Walking Ballista + Contagion Engine is disgusting.",
                "feedback_rating": 5,
            },
            {
                "player": "control_carl",
                "deck_name": "GBW Counters Control",
                "archetype": "control",
                "archetype_detail": "abzan counters control",
                "colors": ["W", "B", "G"],
                "card_names": [
                    "Evolution Sage","Bloated Contaminator","Tireless Tracker","Hardened Scales",
                    "Doubling Season","Ozolith, the Shattered Spire","Varolz, the Scar-Striped",
                    "Hapatra, Vizier of Poisons","Woe Strider","Sanctuary Warden","Yawgmoth, Thran Physician",
                    "Falco Spara, Pactweaver","Wither and Bloom","Smell Fear","Sunfall",
                    "Elspeth Conquers Death","Gix's Command","Contagion Engine","Overgrown Tomb",
                    "Godless Shrine","Temple Garden","Marsh Flats","Indatha Triome",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "Abzan was consistent and powerful. Falco Spara provided insane late-game value.",
                "feedback_rating": 4,
            },
            {
                "player": "midrange_mia",
                "deck_name": "RG Haste Aggro",
                "archetype": "aggro",
                "archetype_detail": "gruul haste aggro",
                "colors": ["R", "G"],
                "card_names": [
                    "Cacophony Scamp","Akki Ember-Keeper","Goro-Goro, Disciple of Ryusei",
                    "Ian the Reckless","Amped Raptor","Legion Warboss","Voldaren Thrillseeker",
                    "Thundering Raiju","Overlord of the Boilerbilges","Halana and Alena, Partners",
                    "Scavenging Ooze","Strangleroot Geist","Young Wolf","Bloated Contaminator",
                    "Bloodthirsty Adversary","Chandra, Pyromaster","Abrade","Volt Charge",
                    "Raging Ravine","Stomping Ground","Rootbound Crag","Wooded Foothills",
                    "Ziatora's Proving Ground",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "Gruul felt one step behind the izzet artifacts deck all tournament.",
                "feedback_rating": 3,
            },
            {
                "player": "combo_ben",
                "deck_name": "BG Proliferate Midrange",
                "archetype": "midrange",
                "archetype_detail": "golgari proliferate",
                "colors": ["B", "G"],
                "card_names": [
                    "Deathbonnet Sprout","Blightbelly Rat","Necroskitter","Mutated Cultist",
                    "Obsessive Skinner","Evolution Sage","Bloated Contaminator","Cankerbloom",
                    "Yawgmoth, Thran Physician","Hapatra, Vizier of Poisons","Woe Strider",
                    "Body Launderer","Wither and Bloom","Grim Affliction","Drown in Ichor",
                    "Contagion Clasp","Carnivorous Canopy","Smell Fear","Overgrown Tomb",
                    "Hissing Quagmire","Woodland Cemetery","Verdant Catacombs","Zagoth Triome",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "Solid deck but just too slow. Needed more early interaction.",
                "feedback_rating": 3,
            },
            {
                "player": "tempo_tara",
                "deck_name": "UW Control",
                "archetype": "control",
                "archetype_detail": "azorius hard control",
                "colors": ["W", "U"],
                "card_names": [
                    "Elspeth Resplendent","Sanctuary Warden","The Wandering Emperor","Ajani Steadfast",
                    "Jace, the Mind Sculptor","Teferi, Temporal Pilgrim","Oath of Teferi",
                    "Dovin, Grand Arbiter","Counterspell","Mana Leak","Serum Snare","Reject Imperfection",
                    "Saruman's Trickery","Out of Time","Swift Reconfiguration","Parting Gust",
                    "Wrath of the Skies","Sunfall","Hallowed Fountain","Glacial Fortress",
                    "Restless Anchorage","Flooded Strand","Spara's Headquarters",
                ],
                "wins": 0, "losses": 3,
                "feedback_comment": "UW hard control is too slow. Artifacts just went under everything.",
                "feedback_rating": 2,
            },
        ],
    },
    {
        "name": "Peasant Cube Draft #5",
        "date_offset_days": -2,
        "decks": [
            {
                "player": "demo",
                "deck_name": "4-Color Proliferate",
                "archetype": "combo",
                "archetype_detail": "4-color proliferate",
                "colors": ["W", "U", "B", "G"],
                "card_names": [
                    "Thrummingbird","Flux Channeler","Viral Drake","Deepglow Skate",
                    "Tekuthal, Inquiry Dominus","Ezuri, Stalker of Spheres","Atraxa, Praetors' Voice",
                    "Doubling Season","Ichormoon Gauntlet","Oath of Teferi","Tezzeret's Gambit",
                    "Ripples of Potential","Contagion Clasp","Contagion Engine","Counterspell",
                    "Mana Leak","Gix's Command","Wither and Bloom","Mana Confluence",
                    "Gemstone Mine","Fabled Passage","Prismatic Vista","Zagoth Triome",
                ],
                "wins": 3, "losses": 0,
                "feedback_comment": "Best deck I've ever drafted in this cube. Atraxa was insane.",
                "feedback_rating": 5,
            },
            {
                "player": "aggro_alex",
                "deck_name": "WG Counters Aggro",
                "archetype": "aggro",
                "archetype_detail": "selesnya counters aggro",
                "colors": ["W", "G"],
                "card_names": [
                    "Guide of Souls","Hopeful Initiate","Luminarch Aspirant","Anafenza, Kin-Tree Spirit",
                    "Emiel the Blessed","Basri's Lieutenant","Sovereign Okinec Ahau",
                    "Scurry Oak","Rosie Cotton of South Lane","Evolution Sage","Hardened Scales",
                    "Doubling Season","Inscription of Abundance","Dromoka's Command",
                    "Ajani, Sleeper Agent","Vivien, Monsters' Advocate","Walking Ballista",
                    "Hangarback Walker","Temple Garden","Sunpetal Grove","Restless Prairie",
                    "Windswept Heath","Jetmir's Garden",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "WG counters was explosive but the proliferate deck had too much inevitability.",
                "feedback_rating": 4,
            },
            {
                "player": "control_carl",
                "deck_name": "UB Proliferate Control",
                "archetype": "control",
                "archetype_detail": "dimir proliferate control",
                "colors": ["U", "B"],
                "card_names": [
                    "Thrummingbird","Flux Channeler","Viral Drake","Glen Elendra Archmage",
                    "Tekuthal, Inquiry Dominus","Jace, the Mind Sculptor","Teferi, Temporal Pilgrim",
                    "Liliana of the Veil","Vraska, Betrayal's Sting","Counterspell","Mana Leak",
                    "Serum Snare","Grim Affliction","Drown in Ichor","Black Sun's Zenith",
                    "Contagion Clasp","Ichormoon Gauntlet","Proft's Eidetic Memory",
                    "Creeping Tar Pit","Watery Grave","Drowned Catacomb","Polluted Delta",
                    "Raffine's Tower",
                ],
                "wins": 2, "losses": 1,
                "feedback_comment": "This deck was great, Glen Elendra Archmage was MVP.",
                "feedback_rating": 4,
            },
            {
                "player": "midrange_mia",
                "deck_name": "BG Graveyard Value",
                "archetype": "midrange",
                "archetype_detail": "golgari graveyard",
                "colors": ["B", "G"],
                "card_names": [
                    "Golgari Grave-Troll","Varolz, the Scar-Striped","Lotleth Troll",
                    "Body Launderer","Hapatra, Vizier of Poisons","Yawgmoth, Thran Physician",
                    "Urborg Scavengers","Massacre Girl, Known Killer","Scavenging Ooze",
                    "Tireless Tracker","Evolution Witness","Woe Strider","Smell Fear",
                    "Carnivorous Canopy","Grim Affliction","Wither and Bloom","Makeshift Mannequin",
                    "The Cruelty of Gix","Overgrown Tomb","Hissing Quagmire","Woodland Cemetery",
                    "Verdant Catacombs","Zagoth Triome",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "Graveyard value was interesting but the proliferate deck just did more.",
                "feedback_rating": 3,
            },
            {
                "player": "combo_ben",
                "deck_name": "RW Tokens/Counters",
                "archetype": "aggro",
                "archetype_detail": "boros tokens",
                "colors": ["W", "R"],
                "card_names": [
                    "Assemble the Legion","Anim Pakal, Thousandth Moon","Ambitious Farmhand",
                    "Legion Warboss","Bright-Palm, Soul Awakener","Cayth, Famed Mechanist",
                    "Guide of Souls","Luminarch Aspirant","Akki Battle Squad","Goro-Goro, Disciple of Ryusei",
                    "Kami of Celebration","Chandra, Acolyte of Flame","Ajani Steadfast",
                    "Ion Storm","Volt Charge","Ordeal of Purphoros","Unbounded Potential",
                    "Curse of Predation","Sacred Foundry","Clifftop Retreat","Restless Bivouac",
                    "Arid Mesa","Savai Triome",
                ],
                "wins": 1, "losses": 2,
                "feedback_comment": "Boros was fun but struggled against the bigger decks.",
                "feedback_rating": 3,
            },
            {
                "player": "tempo_tara",
                "deck_name": "UR Tempo Spells",
                "archetype": "midrange",
                "archetype_detail": "izzet tempo",
                "colors": ["U", "R"],
                "card_names": [
                    "Mercurial Spelldancer","Ledger Shredder","Spectral Adversary","Danny Pink",
                    "Bloodthirsty Adversary","Runaway Steam-Kin","Jace, Vryn's Prodigy",
                    "Chandra, Acolyte of Flame","Ral, Izzet Viceroy","Counterspell","Mana Leak",
                    "Experimental Augury","Aether Spike","Tune the Narrative","Ripples of Potential",
                    "Volt Charge","Galvanic Discharge","Radstorm","Steam Vents","Sulfur Falls",
                    "Wandering Fumarole","Scalding Tarn","Raugrin Triome",
                ],
                "wins": 0, "losses": 3,
                "feedback_comment": "UR tempo felt too low on threats. Needs more proactive cards.",
                "feedback_rating": 2,
            },
        ],
    },
]

# Card feedback data (card_name -> list of (rating, comment) tuples)
CARD_FEEDBACK_DATA = {
    "Yawgmoth, Thran Physician": [
        (5, "Absolutely dominates every game. Way too powerful for this cube."),
        (4, "Incredible engine. Perhaps too consistent."),
        (5, "Best card in the cube. Wins games on the spot with counters."),
    ],
    "Deepglow Skate": [
        (5, "Deepglow Skate wins the game immediately when it resolves."),
        (4, "Insane with planeswalkers. Feels necessary to answer immediately."),
    ],
    "Contagion Engine": [
        (5, "This card is a one-card army. Probably too powerful to print effects on."),
        (4, "Wins most games it's cast. Very strong."),
    ],
    "Walking Ballista": [
        (4, "Great utility card. Scales well, not oppressive."),
        (4, "Perfect support piece. Good in many strategies."),
    ],
    "Atraxa, Praetors' Voice": [
        (5, "Atraxa is a house. Might be too much for the format."),
        (4, "Insane in the right shell but requires setup."),
    ],
    "Doubling Season": [
        (5, "Too strong when combined with planeswalkers. Feels broken."),
        (4, "Very powerful but requires specific setup."),
    ],
    "Ledger Shredder": [
        (4, "Super consistent. Gets huge quickly in a spells deck."),
        (3, "Good but manageable. Fair card."),
    ],
    "Thrummingbird": [
        (4, "Essential proliferate engine. Very consistent."),
        (3, "Good in its deck, flexible enough."),
    ],
    "Runaway Steam-Kin": [
        (4, "Generates so much mana in a spells deck. Underrated."),
        (3, "Solid but not oppressive."),
    ],
    "Elspeth Conquers Death": [
        (3, "Decent role-player. Not exciting but solid."),
        (3, "Good catch-all."),
    ],
    "Wrath of the Skies": [
        (4, "Great wrath effect. Very necessary for this format."),
        (3, "Balanced reset button."),
    ],
    "Anafenza, Kin-Tree Spirit": [
        (4, "Great at enabling counters synergies without being broken."),
        (4, "Perfect 2-drop for white counters decks."),
    ],
    "Flux Channeler": [
        (4, "Super consistent proliferate trigger. Love this card."),
        (4, "One of the glue cards that makes proliferate work."),
    ],
    "Counterspell": [
        (4, "Core control piece. Well-balanced in this cube."),
        (3, "Good, not oppressive. Format needs answers."),
    ],
    "Sunfall": [
        (4, "Excellent sweeper. Makes white control viable."),
        (3, "Strong but fair."),
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_user(db, username, email, password):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        log.info("User %s already exists, skipping", username)
        return existing
    u = User(
        username=username,
        email=email,
        hashed_password=_pwd.hash(password),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    log.info("Created user %s", username)
    return u


def _fetch_and_store_cards(db, card_names: list[str]) -> dict[str, int]:
    """
    Ensure all card_names exist in the DB.
    Returns {card_name: card_id}.
    """
    # Deduplicate
    unique_names = list(dict.fromkeys(card_names))
    result: dict[str, int] = {}

    # Check what's already in DB
    missing = []
    for name in unique_names:
        card = CardService.get_card_by_name(db, name)
        if card:
            result[name] = card.id
        else:
            missing.append(name)

    if not missing:
        return result

    log.info("Fetching %d cards from Scryfall (batched)…", len(missing))
    scryfall_result = ScryfallService.get_cards_by_names_bulk(missing)
    found_data = scryfall_result.get("found", [])
    not_found = scryfall_result.get("not_found", [])
    if not_found:
        log.warning("Scryfall could not find: %s", not_found)

    for card_data in found_data:
        name = card_data.get("name", "")
        # For DFC cards Scryfall returns "Front // Back" — match by front face
        matched_name = name
        if " // " in name:
            front = name.split(" // ")[0].strip()
            if front in [m.split(" // ")[0].strip() for m in missing]:
                matched_name = name

        # Check exact or front-face match
        existing = CardService.get_card_by_name(db, matched_name)
        if existing:
            result[matched_name] = existing.id
            # Also map without " // back" suffix
            if " // " in matched_name:
                result[matched_name.split(" // ")[0].strip()] = existing.id
            continue

        # Determine front-face colors/mana_cost for DFC
        colors = card_data.get("colors")
        mana_cost = card_data.get("mana_cost")
        type_line = card_data.get("type_line")
        oracle_text = card_data.get("oracle_text")
        if not colors and "card_faces" in card_data:
            face = card_data["card_faces"][0]
            colors = face.get("colors", [])
            mana_cost = face.get("mana_cost", "")
            type_line = face.get("type_line", type_line)
            oracle_text = face.get("oracle_text", oracle_text)

        image_uris = card_data.get("image_uris", {})
        if not image_uris and "card_faces" in card_data:
            image_uris = card_data["card_faces"][0].get("image_uris", {})

        card = CardService.create_card_with_details(
            db=db,
            name=matched_name,
            scryfall_id=card_data.get("id", ""),
            mana_cost=mana_cost,
            type_line=type_line,
            colors=colors or [],
            cmc=card_data.get("cmc"),
            power=card_data.get("power"),
            toughness=card_data.get("toughness"),
            oracle_text=oracle_text,
            image_url=image_uris.get("normal"),
            small_image_url=image_uris.get("small"),
            rarity=card_data.get("rarity"),
            set_code=card_data.get("set"),
            set_name=card_data.get("set_name"),
            scryfall_uri=card_data.get("scryfall_uri"),
        )
        result[matched_name] = card.id
        if " // " in matched_name:
            result[matched_name.split(" // ")[0].strip()] = card.id
        log.debug("  Stored card: %s", matched_name)
        time.sleep(0.05)  # Scryfall rate limit courtesy

    return result


def _get_or_create_cube(db, owner_id: int, name_map: dict[str, int]) -> Cube:
    existing = db.query(Cube).filter(
        Cube.owner_id == owner_id,
        Cube.name == "Peasant Power Cube",
    ).first()
    if existing:
        log.info("Cube already exists (id=%d), skipping card population", existing.id)
        return existing

    cube = Cube(
        name="Peasant Power Cube",
        description=(
            "A powered peasant cube focusing on +1/+1 counters, proliferate, "
            "and graveyard synergies across all colour pairs."
        ),
        owner_id=owner_id,
        life_total=20,
        pack_count=3,
        pack_size=15,
        draft_rules="Winston draft or Rochester for < 4 players.",
        gameplay_rules="Best of 1 matches. 20 minute rounds.",
    )
    db.add(cube)
    db.commit()
    db.refresh(cube)
    log.info("Created cube (id=%d)", cube.id)

    added = 0
    for card_name in CUBE_CARDS:
        cid = name_map.get(card_name) or name_map.get(card_name.split(" // ")[0].strip())
        if not cid:
            log.warning("Card not in name_map, skipping cube add: %s", card_name)
            continue
        already = db.query(CubeCard).filter(
            CubeCard.cube_id == cube.id,
            CubeCard.card_id == cid,
        ).first()
        if not already:
            db.add(CubeCard(cube_id=cube.id, card_id=cid, quantity=1))
            added += 1
    db.commit()
    log.info("Added %d cards to cube", added)
    return cube


def _generate_ai_description(deck_data: dict, card_name_map: dict) -> str:
    card_names = [
        card_name_map.get(cid, "Unknown") if isinstance(cid, int) else cid
        for cid in deck_data["card_names"]
    ]
    try:
        desc = AIService.generate_deck_description(
            player_name=deck_data["player"],
            deck_name=deck_data["deck_name"],
            card_names=card_names,
            record=f"{deck_data['wins']}-{deck_data['losses']}",
        )
        log.info("    AI description generated for %s", deck_data["deck_name"])
        return desc
    except Exception as e:
        log.warning("    AI description failed: %s", e)
        return f"A {deck_data['archetype_detail']} deck going {deck_data['wins']}-{deck_data['losses']}."


def _generate_ai_draft_summary(event, cube, decks_data: list[dict]) -> str:
    deck_dict_list = [
        {
            "player_name": d["player"],
            "deck_name": d["deck_name"],
            "record": f"{d['wins']}-{d['losses']}",
            "ai_description": d.get("ai_desc", ""),
            "card_names": d["card_names"],
        }
        for d in decks_data
    ]
    try:
        summary = AIService.generate_draft_summary(
            draft_name=event.name,
            cube_name=cube.name,
            decks=deck_dict_list,
        )
        log.info("  AI draft summary generated")
        return summary
    except Exception as e:
        log.warning("  AI draft summary failed: %s", e)
        return f"Draft {event.name} completed with {len(decks_data)} players."


# ---------------------------------------------------------------------------
# Main seed
# ---------------------------------------------------------------------------

def seed():
    db = SessionLocal()
    try:
        # ── 1. Create users ──────────────────────────────────────────────────
        log.info("=== Step 1: Users ===")
        demo_user = _get_or_create_user(db, "demo_owner", "demo@cube.test", "demopass123")
        fake_users: dict[str, User] = {"demo": demo_user}
        for p in FAKE_PLAYERS:
            fake_users[p["username"]] = _get_or_create_user(db, p["username"], p["email"], p["password"])

        # ── 2. Fetch all cube cards from Scryfall ────────────────────────────
        log.info("=== Step 2: Fetching cube cards from Scryfall ===")
        # Collect all unique card names needed (cube list + all deck lists)
        all_names: set[str] = set(CUBE_CARDS)
        for scenario in DRAFT_SCENARIOS:
            for deck in scenario["decks"]:
                all_names.update(deck["card_names"])
        name_map = _fetch_and_store_cards(db, list(all_names))
        log.info("Card name_map has %d entries", len(name_map))

        # ── 3. Create cube ───────────────────────────────────────────────────
        log.info("=== Step 3: Cube ===")
        cube = _get_or_create_cube(db, demo_user.id, name_map)

        # ── 4. Draft events ──────────────────────────────────────────────────
        log.info("=== Step 4: Draft Events ===")
        from datetime import datetime, timedelta

        for scenario in DRAFT_SCENARIOS:
            existing_event = db.query(DraftEvent).filter(
                DraftEvent.cube_id == cube.id,
                DraftEvent.name == scenario["name"],
            ).first()
            if existing_event:
                log.info("  Event '%s' already exists, skipping", scenario["name"])
                continue

            event_date = datetime.utcnow() + timedelta(days=scenario["date_offset_days"])

            event = DraftEvent(
                cube_id=cube.id,
                password_hash=_pwd.hash("eventpass"),
                name=scenario["name"],
                status="completed",
                num_players=len(scenario["decks"]),
                event_type="hosted",
                num_rounds=3,
                best_of=1,
                current_round=3,
                created_at=event_date,
                updated_at=event_date,
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            log.info("  Created event: %s (id=%d)", event.name, event.id)

            # Add participants
            for deck_data in scenario["decks"]:
                player_key = deck_data["player"]
                user = fake_users.get(player_key)
                if user:
                    already = db.query(DraftParticipant).filter_by(
                        draft_event_id=event.id, user_id=user.id
                    ).first()
                    if not already:
                        db.add(DraftParticipant(
                            draft_event_id=event.id,
                            user_id=user.id,
                            joined_at=event_date,
                        ))
            db.commit()

            # Create decks
            created_decks = []
            for i, deck_data in enumerate(scenario["decks"]):
                player_key = deck_data["player"]
                user = fake_users.get(player_key)

                # Resolve card names -> IDs
                card_ids = []
                for cname in deck_data["card_names"]:
                    cid = name_map.get(cname) or name_map.get(cname.split(" // ")[0].strip())
                    if cid:
                        card_ids.append(cid)
                    else:
                        log.warning("    Missing card in name_map: %s", cname)

                # Build color identity from actual card data
                color_identity = UserDeckService.compute_color_identity(db, card_ids)

                # Generate AI deck description
                log.info("    Generating AI desc for: %s", deck_data["deck_name"])
                ai_desc = _generate_ai_description(deck_data, {})
                deck_data["ai_desc"] = ai_desc
                time.sleep(1)  # Be gentle with the AI API

                record = f"{deck_data['wins']}-{deck_data['losses']}"
                ud = UserDeck(
                    user_id=user.id if user else None,
                    draft_event_id=event.id,
                    player_name=player_key,
                    deck_name=deck_data["deck_name"],
                    deck_cards=json.dumps(card_ids),
                    sideboard_cards=json.dumps([]),
                    full_pool_cards=json.dumps(card_ids),
                    wins=deck_data["wins"],
                    losses=deck_data["losses"],
                    record=record,
                    ai_description=ai_desc,
                    archetype=deck_data["archetype"],
                    archetype_detail=deck_data["archetype_detail"],
                    color_identity=color_identity,
                    created_at=event_date,
                )
                db.add(ud)
                db.commit()
                db.refresh(ud)
                created_decks.append(ud)
                log.info("    Deck created: %s (%s)", deck_data["deck_name"], record)

            # Create Swiss rounds and pairings (3 rounds, 6 players)
            player_deck_map = {
                fake_users[d["player"]].id: created_decks[i]
                for i, d in enumerate(scenario["decks"])
                if d["player"] in fake_users
            }
            user_ids = list(player_deck_map.keys())
            random.shuffle(user_ids)

            for round_num in range(1, 4):
                r = DraftRound(
                    draft_event_id=event.id,
                    round_number=round_num,
                    status="complete",
                    created_at=event_date,
                )
                db.add(r)
                db.commit()
                db.refresh(r)

                # Simple round-robin pairing for seed purposes
                paired = list(user_ids)
                while len(paired) % 2 != 0:
                    paired.append(None)  # bye
                for j in range(0, len(paired), 2):
                    u1_id = paired[j]
                    u2_id = paired[j + 1]
                    deck1 = player_deck_map.get(u1_id)
                    deck2 = player_deck_map.get(u2_id) if u2_id else None

                    # Determine winner based on deck records
                    if u2_id is None:
                        winner_id = u1_id
                        p1w, p2w = 1, 0
                    else:
                        w1 = player_deck_map[u1_id].wins
                        w2 = player_deck_map[u2_id].wins
                        if w1 >= w2:
                            winner_id = u1_id
                            p1w, p2w = 2, 1
                        else:
                            winner_id = u2_id
                            p1w, p2w = 1, 2

                    pairing = DraftPairing(
                        round_id=r.id,
                        player1_user_id=u1_id,
                        player2_user_id=u2_id,
                        player1_deck_id=deck1.id if deck1 else None,
                        player2_deck_id=deck2.id if deck2 else None,
                        player1_wins=p1w,
                        player2_wins=p2w,
                        winner_user_id=winner_id,
                        player1_confirmed="yes",
                        player2_confirmed="yes" if u2_id else "yes",
                        status="complete",
                        created_at=event_date,
                    )
                    db.add(pairing)
                # Rotate pairings for next round (simple shift)
                user_ids = user_ids[1:] + [user_ids[0]]
            db.commit()

            # Generate AI draft summary
            log.info("  Generating AI draft summary…")
            summary = _generate_ai_draft_summary(event, cube, scenario["decks"])
            event.ai_summary = summary
            db.commit()

            # Per-event feedback from each player
            for deck_data in scenario["decks"]:
                player_key = deck_data["player"]
                user = fake_users.get(player_key)
                if not user:
                    continue
                existing_fb = db.query(Feedback).filter_by(
                    user_id=user.id, draft_event_id=event.id
                ).first()
                if not existing_fb:
                    db.add(Feedback(
                        user_id=user.id,
                        draft_event_id=event.id,
                        rating=deck_data["feedback_rating"],
                        comment=deck_data["feedback_comment"],
                    ))
            db.commit()

            # Post-draft feedback (standout/underperformer cards)
            for i, deck_data in enumerate(scenario["decks"]):
                player_key = deck_data["player"]
                user = fake_users.get(player_key)
                if not user:
                    continue
                card_ids_for_deck = [
                    name_map.get(cn) or name_map.get(cn.split(" // ")[0].strip())
                    for cn in deck_data["card_names"]
                    if name_map.get(cn) or name_map.get(cn.split(" // ")[0].strip())
                ]
                # Standout = last 3 cards (highest impact for this deck)
                standout_ids = card_ids_for_deck[-3:] if len(card_ids_for_deck) >= 3 else card_ids_for_deck
                # Underperformer = first 2 cards
                underperformer_ids = card_ids_for_deck[:2]

                existing_pdf = db.query(PostDraftFeedback).filter_by(
                    user_id=user.id, draft_event_id=event.id
                ).first()
                if not existing_pdf:
                    db.add(PostDraftFeedback(
                        draft_event_id=event.id,
                        user_id=user.id,
                        player_name=player_key,
                        overall_rating=deck_data["feedback_rating"],
                        overall_thoughts=deck_data["feedback_comment"],
                        standout_card_ids=json.dumps(standout_ids),
                        underperformer_card_ids=json.dumps(underperformer_ids),
                        recommendations_for_owner=(
                            "Consider cutting some of the underperforming lands and "
                            "adding more early interaction." if deck_data["wins"] < 2 else
                            "The counters shell is very well supported — great cube design!"
                        ),
                    ))
            db.commit()
            log.info("  Feedback recorded for event: %s", event.name)

        # ── 5. Card feedback across all events ───────────────────────────────
        log.info("=== Step 5: Card Feedback ===")
        all_events = db.query(DraftEvent).filter(DraftEvent.cube_id == cube.id).all()
        rater_user = demo_user

        for card_name, feedback_list in CARD_FEEDBACK_DATA.items():
            cid = name_map.get(card_name)
            if not cid:
                log.warning("Card not in name_map for feedback: %s", card_name)
                continue
            for event in all_events[:len(feedback_list)]:
                rating, comment = feedback_list[all_events.index(event) % len(feedback_list)]
                existing = db.query(CardFeedback).filter_by(
                    user_id=rater_user.id,
                    card_id=cid,
                    draft_event_id=event.id,
                ).first()
                if not existing:
                    db.add(CardFeedback(
                        user_id=rater_user.id,
                        card_id=cid,
                        draft_event_id=event.id,
                        feedback_type="cube_specific",
                        rating=rating,
                        comment=comment,
                    ))
        db.commit()
        log.info("Card feedback recorded")

        log.info("")
        log.info("=== Seed complete! ===")
        log.info("Login: demo@cube.test / demopass123")
        log.info("Cube: 'Peasant Power Cube' owned by demo_owner")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
