# Cube Foundry - Quick Start Guide

## Running the Application

### Backend (FastAPI + PostgreSQL)

1. **Set up PostgreSQL Database**:

   ```bash
   # Create database in PostgreSQL
   psql -U postgres
   CREATE DATABASE cube_foundry;
   \q
   ```

2. **Configure Backend**:

   ```bash
   cd back_end

   # Copy and edit .env
   cp .env.example .env
   # Edit .env with your PostgreSQL credentials
   ```

3. **Install Backend Dependencies**:

   ```bash
   # Make sure virtual environment is activated
   .\venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

4. **Run Backend**:

   ```bash
   uvicorn main:app --reload
   ```

   Backend will be available at: `http://localhost:8000`
   API docs at: `http://localhost:8000/docs`

### Frontend (React + Vite)

1. **Install Frontend Dependencies** (already done):

   ```bash
   cd front_end
   npm install
   ```

2. **Run Frontend**:

   ```bash
   npm run dev
   ```

   Frontend will be available at: `http://localhost:3000`

## First Steps

1. Open `http://localhost:3000` in your browser
2. Click "Sign Up" to create an account
3. After registration, you'll be redirected to the Dashboard
4. Click "Create New Cube" to get started
5. Add cards by searching Scryfall

## What's Implemented

### ✅ Working Features

- **Authentication**:
  - User registration with validation
  - User login
  - Protected routes
  - Auth state management

- **Cube Management**:
  - Create cubes with name/description
  - View all your cubes
  - View cube details
  - Add cards from Scryfall
  - Remove cards from cube
  - Delete cubes

- **Scryfall Integration**:
  - Search cards by name
  - Card image preview
  - Automatic card data caching
  - Add cards to database on-demand

### 🚧 To Be Implemented

- Draft event hosting and joining
- Deck photo upload and OCR
- Card feedback system (general + cube-specific)
- Analytics and performance tracking
- Card recommendations using vector similarity
- User performance statistics
- Event password verification

## Project Structure

```
cubeanalyticssoftware/
├── back_end/              # FastAPI backend
│   ├── api/
│   │   ├── endpoints/     # API routes
│   │   ├── models/        # SQLAlchemy models
│   │   ├── services/      # Business logic
│   │   └── schemas.py     # Pydantic schemas
│   ├── main.py            # FastAPI app
│   ├── database.py        # DB config
│   └── requirements.txt
│
└── front_end/             # React frontend
    ├── src/
    │   ├── api/           # API client
    │   ├── auth/          # Auth context
    │   ├── components/    # UI components
    │   ├── pages/         # Page components
    │   └── routes/        # Routing
    └── package.json
```

## Development Workflow

### Adding New Features

1. **Backend**:
   - Add models in `back_end/api/models/`
   - Add schemas in `back_end/api/schemas.py`
   - Add service in `back_end/api/services/`
   - Add endpoints in `back_end/api/endpoints/`
   - Register router in `back_end/main.py`

2. **Frontend**:
   - Add API calls in `front_end/src/api/`
   - Create page components in `front_end/src/pages/`
   - Add routes in `front_end/src/routes/AppRoutes.tsx`
   - Use React Query for data fetching

### Database Migrations

Currently using SQLAlchemy's `create_all()` for development. For production, consider adding Alembic:

```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

## Troubleshooting

### Backend Issues

- **Database connection error**: Check PostgreSQL is running and credentials in `.env`
- **Module not found**: Activate venv and run `pip install -r requirements.txt`
- **Port already in use**: Change port with `uvicorn main:app --port 8001`

### Frontend Issues

- **API connection error**: Ensure backend is running on port 8000
- **CORS error**: Backend already configured for CORS, refresh browser
- **Build errors**: Delete `node_modules` and run `npm install` again

### Common Issues

- **Cards not appearing**: Check Scryfall API is accessible (not rate-limited)
- **Auth not persisting**: Check browser localStorage is enabled
- **Images not loading**: Scryfall image URLs may expire, refresh the page

## Next Development Priorities

1. **Draft Events** (high priority):
   - Create draft event UI
   - Join event with password
   - Event listing page

2. **Deck Management** (high priority):
   - Upload deck photos
   - OCR/AI card recognition
   - Record tracking (3-0, 2-1, etc.)

3. **Card Feedback** (medium priority):
   - Feedback forms (general + cube-specific)
   - Vector storage via Chroma DB
   - Aggregated feedback display

4. **Analytics** (medium priority):
   - Card performance charts
   - Player statistics
   - Win rate tracking
   - Cards drafted vs played

5. **Recommendations** (lower priority):
   - Vector similarity search
   - Suggest cards based on cube context
   - ML-powered recommendations

## Deployment

See individual READMEs:

- `back_end/README.md` - Backend deployment to Azure
- `front_end/README.md` - Frontend deployment to Azure Static Web Apps

## Contributing

This is a personal project for Magic: The Gathering cube management and analytics.
