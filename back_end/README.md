# Cube Foundry Backend

FastAPI backend for Cube Foundry - a platform for Magic: The Gathering cube management and analytics.

## Project Structure

```
back_end/
├── api/
│   ├── endpoints/          # API endpoints
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── cubes.py       # Cube management endpoints
│   │   ├── draft_events.py # Draft event endpoints
│   │   ├── decks.py       # User deck endpoints
│   │   └── feedback.py    # Feedback endpoints
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py
│   │   ├── cube.py
│   │   ├── draft_event.py
│   │   ├── user_deck.py
│   │   └── feedback.py
│   ├── services/          # Business logic services
│   │   ├── user_service.py
│   │   ├── cube_service.py
│   │   ├── draft_event_service.py
│   │   ├── user_deck_service.py
│   │   └── feedback_service.py
│   └── schemas.py         # Pydantic schemas for validation
├── main.py                # FastAPI app entry point
├── database.py            # Database configuration
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Setup Instructions

### 1. Create a Virtual Environment

```bash
python -m venv venv
this should be using python 3.12
.\venv\Scripts\activate  # On Windows
source venv/bin/activate # On macOS/Linux
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and update with your configuration:

```bash
cp .env.example .env
```

Update the DATABASE_URL in `.env`:

```
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/cube_foundry
```

### 4. Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE cube_foundry;

# Exit psql
\q
```

### 5. Run the Application

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

API Documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login a user

### Cubes

- `POST /cubes/` - Create a new cube
- `GET /cubes/{cube_id}` - Get a cube
- `GET /cubes/owner/{owner_id}` - Get cubes by owner
- `GET /cubes/` - Get all cubes
- `PUT /cubes/{cube_id}` - Update a cube
- `DELETE /cubes/{cube_id}` - Delete a cube
- `GET /cubes/{cube_id}/cards` - Get cards in a cube

### Draft Events

- `POST /events/` - Create a draft event
- `GET /events/{event_id}` - Get a draft event
- `GET /events/cube/{cube_id}` - Get events for a cube
- `POST /events/{event_id}/verify-password` - Verify event password
- `DELETE /events/{event_id}` - Delete an event

### Decks

- `POST /decks/` - Create a user deck
- `GET /decks/{deck_id}` - Get a deck
- `GET /decks/user/{user_id}` - Get user's decks
- `GET /decks/event/{event_id}` - Get decks for an event
- `DELETE /decks/{deck_id}` - Delete a deck
- `GET /decks/{deck_id}/cards` - Get deck cards

### Feedback

- `POST /feedback/` - Create feedback
- `GET /feedback/{feedback_id}` - Get feedback
- `GET /feedback/event/{event_id}` - Get feedback for an event
- `GET /feedback/user/{user_id}` - Get user's feedback
- `DELETE /feedback/{feedback_id}` - Delete feedback
- `GET /feedback/event/{event_id}/average-rating` - Get event average rating

## Architecture

The backend follows a clean architecture pattern:

- **Endpoints**: Handle HTTP requests/responses and validation using Pydantic schemas
- **Services**: Contain business logic and database operations using SQLAlchemy
- **Models**: Define database schema and relationships
- **Schemas**: Pydantic models for request/response validation

## Database Models

- **User**: User accounts with authentication
- **Cube**: Magic: The Gathering cubes created by users
- **DraftEvent**: Events where cubes are drafted
- **UserDeck**: Decks created by users during draft events
- **Feedback**: User feedback on draft events and cubes

## Security Considerations

- Passwords are hashed using bcrypt via `passlib`
- Draft event passwords are also hashed
- CORS is configured for frontend integration
- Environment variables for sensitive data

## Deployment to Azure

To deploy to Azure:

1. Create an Azure App Service
2. Set up an Azure PostgreSQL database
3. Configure environment variables in Azure App Service settings
4. Deploy using Azure DevOps or Git integration

See Azure documentation for detailed deployment instructions.

## Future Enhancements

- Image analysis service for AI card recognition
- Analytics and reporting endpoints
- User performance tracking
- Advanced card analytics
- WebSocket support for real-time updates
