'use client'

import { useState } from 'react'
import { trpc } from '@/utils/trpc'

export default function Home() {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState<string | null>(
    typeof window !== 'undefined' ? localStorage.getItem('token') : null
  )

  const signup = trpc.auth.signup.useMutation()
  const login = trpc.auth.login.useMutation()
  const { data: helloData } = trpc.hello.useQuery(undefined, {
    enabled: !!token,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const result = isLogin
        ? await login.mutateAsync({ email, password })
        : await signup.mutateAsync({ email, password })
      
      if (result.token) {
        localStorage.setItem('token', result.token)
        setToken(result.token)
      }
    } catch (error) {
      console.error('Auth error:', error)
    }
  }

  if (token && helloData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <h1 className="text-4xl font-bold">{helloData.greeting}</h1>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="w-full max-w-md space-y-8 p-8">
        <div>
          <h2 className="text-3xl font-bold text-center">
            {isLogin ? 'Login' : 'Sign Up'}
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
          <button
            type="submit"
            disabled={signup.isPending || login.isPending}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {signup.isPending || login.isPending
              ? 'Loading...'
              : isLogin
              ? 'Login'
              : 'Sign Up'}
          </button>
        </form>
        <button
          onClick={() => setIsLogin(!isLogin)}
          className="w-full text-sm text-blue-600 hover:underline"
        >
          {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Login'}
        </button>
        {(signup.error || login.error) && (
          <div className="text-red-600 text-sm text-center">
            {signup.error?.message || login.error?.message}
          </div>
        )}
      </div>
    </div>
  )
}
