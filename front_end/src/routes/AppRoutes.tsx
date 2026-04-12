import { Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '../auth/ProtectedRoute'

// Pages
import LandingPage from '../pages/LandingPage'
import RegisterPage from '../pages/auth/RegisterPage'
import LoginPage from '../pages/auth/LoginPage'
import DashboardPage from '../pages/DashboardPage'
import CubesPage from '../pages/cubes/CubesPage'
import CubeDetailPage from '../pages/cubes/CubeDetailPage'
import CreateCubePage from '../pages/cubes/CreateCubePage'
import CardDetailPage from '../pages/cards/CardDetailPage'
import DraftsPage from '../pages/drafts/DraftsPage'
import DraftDetailPage from '../pages/drafts/DraftDetailPage'
import JoinDraftPage from '../pages/drafts/JoinDraftPage'
import MyDraftsPage from '../pages/drafts/MyDraftsPage'
import ProfilePage from '../pages/profile/ProfilePage'
import AboutPage from '../pages/AboutPage'

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth/register" element={<RegisterPage />} />
      <Route path="/auth/login" element={<LoginPage />} />

      {/* Protected routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cubes"
        element={
          <ProtectedRoute>
            <CubesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cubes/new"
        element={
          <ProtectedRoute>
            <CreateCubePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cubes/:id"
        element={
          <ProtectedRoute>
            <CubeDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cards/:cardId"
        element={
          <ProtectedRoute>
            <CardDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cubes/:id/drafts"
        element={
          <ProtectedRoute>
            <DraftsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cubes/:id/drafts/:draftId"
        element={
          <ProtectedRoute>
            <DraftDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/join-draft"
        element={
          <ProtectedRoute>
            <JoinDraftPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/my-drafts"
        element={
          <ProtectedRoute>
            <MyDraftsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/players/:userId"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />

      {/* Public */}
      <Route path="/about" element={<AboutPage />} />

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRoutes
