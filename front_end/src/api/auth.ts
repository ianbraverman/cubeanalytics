import apiClient from './client'

export interface RegisterData {
  email: string
  username: string
  password: string
}

export interface LoginData {
  email: string
  password: string
}

export interface User {
  id: number
  email: string
  username: string
  created_at: string
}

export const authApi = {
  register: async (data: RegisterData): Promise<User> => {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  },

  login: async (data: LoginData): Promise<User> => {
    const response = await apiClient.post('/auth/login', data)
    return response.data
  },

  // For now, we'll store user in localStorage
  // In production, you'd want a /me endpoint to verify token
  getCurrentUser: (): User | null => {
    const userJson = localStorage.getItem('currentUser')
    return userJson ? JSON.parse(userJson) : null
  },

  setCurrentUser: (user: User) => {
    localStorage.setItem('currentUser', JSON.stringify(user))
  },

  logout: () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('currentUser')
  },
}
