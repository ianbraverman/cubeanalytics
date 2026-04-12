from dotenv import load_dotenv

# Load environment variables FIRST before other imports
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.endpoints import auth, cubes, cards, card_feedback, cube_cards, draft_events, decks, feedback, statistics
from database import engine

app = FastAPI(title="Cube Foundry API")

# Add CORS middleware
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
_allowed_origins = [o.strip() for o in _allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(cards.router, prefix="/cards", tags=["Cards"])
app.include_router(card_feedback.router, prefix="/card-feedback", tags=["Card Feedback"])
app.include_router(cubes.router, prefix="/cubes", tags=["Cubes"])
app.include_router(cube_cards.router, prefix="/cube-cards", tags=["Cube Cards"])
app.include_router(draft_events.router, prefix="/draft-events", tags=["Draft Events"])
app.include_router(decks.router, prefix="/decks", tags=["Decks"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
app.include_router(statistics.router, prefix="/statistics", tags=["Statistics"])

# Serve uploaded deck photos
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/")
async def root():
    return {"message": "Welcome to Cube Foundry API", "version": "0.1.0"}
