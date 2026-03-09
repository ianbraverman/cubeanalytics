# Cube Foundry Frontend

React + TypeScript + Vite frontend for Cube Foundry - a platform for managing and analyzing Magic: The Gathering cubes.

## Features

- ✅ User authentication (register/login)
- ✅ Cube management (create, view, edit, delete)
- ✅ Scryfall integration for card search
- ✅ Add cards to cubes with visual search
- 🚧 Draft event hosting and joining
- 🚧 Deck upload and management
- 🚧 Card feedback system
- 🚧 Analytics and performance tracking

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **React Router v6** for routing
- **TanStack Query (React Query)** for server state management
- **Axios** for API calls
- **React Hook Form + Zod** for forms and validation
- **Tailwind CSS** for styling
- **Zustand** for client state (if needed)

## Project Structure

```
src/
├── api/              # API client and endpoint wrappers
│   ├── client.ts     # Axios instance with interceptors
│   ├── auth.ts       # Auth endpoints
│   ├── cards.ts      # Cards and Scryfall endpoints
│   └── cubes.ts      # Cubes endpoints
├── auth/             # Authentication logic
│   ├── AuthProvider.tsx
│   └── ProtectedRoute.tsx
├── components/       # Reusable UI components
│   └── Layout.tsx
├── pages/            # Page components
│   ├── LandingPage.tsx
│   ├── DashboardPage.tsx
│   ├── auth/
│   │   ├── RegisterPage.tsx
│   │   └── LoginPage.tsx
│   └── cubes/
│       ├── CubesPage.tsx
│       ├── CreateCubePage.tsx
│       └── CubeDetailPage.tsx
├── routes/           # Routing configuration
│   └── AppRoutes.tsx
├── App.tsx           # Root component
└── main.tsx          # Entry point
```

## Getting Started

### Prerequisites

- Node.js 20.x or higher
- npm or yarn

### Installation

1. Install dependencies:

```bash
npm install
```

2. Create a `.env` file (already exists):

```
VITE_API_URL=http://localhost:8000
```

3. Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Backend Setup

Make sure the FastAPI backend is running on `http://localhost:8000`. See the `back_end/README.md` for setup instructions.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## API Integration

The frontend communicates with the FastAPI backend through Axios. The API client (`src/api/client.ts`) includes:

- Base URL configuration
- Request interceptor for auth tokens
- Response interceptor for error handling
- Automatic 401 redirect to login

### Authentication Flow

1. User registers or logs in
2. Backend returns user object
3. User object stored in localStorage
4. Token (if provided) stored in localStorage
5. Token included in all subsequent requests via Axios interceptor

## Key Features

### Cube Management

- Create cubes with name and description
- Search Scryfall for cards and add them to cubes
- View all cards in a cube
- Remove cards from cubes
- Track cube size

### Scryfall Integration

- Real-time card search
- Card image preview
- Automatic card data caching
- Support for all Scryfall search syntax

## Next Steps

### Immediate TODOs

- [ ] Add draft event hosting UI
- [ ] Add event joining and password verification
- [ ] Implement deck photo upload
- [ ] Add card feedback forms
- [ ] Create analytics dashboards
- [ ] Add card recommendations based on vector similarity

### Future Enhancements

- Image upload and AI card recognition
- Real-time event updates (WebSockets)
- Advanced filtering and sorting
- Export/import cube lists
- Social features (following, sharing)
- Mobile responsive improvements
- Dark mode

## Styling

The app uses Tailwind CSS for styling. Key design choices:

- Clean, modern interface
- Focus on card imagery
- Responsive grid layouts
- Blue primary color scheme
- Consistent spacing and typography

## Deployment

### Build for Production

```bash
npm run build
```

This creates a `dist/` folder with optimized static files.

### Deploy to Azure

1. **Azure Static Web Apps** (Recommended):
   - Create a Static Web App in Azure Portal
   - Connect to your GitHub repository
   - Configure build:
     - App location: `/front_end`
     - Output location: `dist`
   - Set environment variable: `VITE_API_URL=https://your-api.azurewebsites.net`

2. **Azure Blob Storage + CDN**:
   - Create a Storage Account
   - Enable Static Website hosting
   - Upload `dist/` contents to `$web` container
   - Configure CDN for custom domain (optional)

## Environment Variables

- `VITE_API_URL` - Backend API URL (default: `http://localhost:8000`)

## Troubleshooting

### CORS Issues

If you see CORS errors, ensure the backend has the frontend URL in its CORS configuration (`main.py`).

### API Connection Errors

- Verify backend is running on the correct port
- Check `VITE_API_URL` in `.env`
- Inspect network requests in browser DevTools

### Build Errors

- Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version: `node --version` (should be 20.x+)

## License

Proprietary - Cube Foundry
