import { useState } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'

function App() {
  const [user, setUser] = useState<string | null>(null)

  const handleLogin = (username: string) => {
    setUser(username)
  }

  if (!user) {
    return <Login onLogin={handleLogin} />
  }

  return <Dashboard />
}

export default App
