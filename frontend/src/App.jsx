import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import BatchUpload from './pages/BatchUpload'
import Analytics from './pages/Analytics'
import ProtectedLayout from './components/ProtectedLayout'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/app"
        element={
          <ProtectedLayout>
            <Dashboard />
          </ProtectedLayout>
        }
      />
      <Route
        path="/app/history"
        element={
          <ProtectedLayout>
            <History />
          </ProtectedLayout>
        }
      />
      <Route
        path="/app/batch"
        element={
          <ProtectedLayout>
            <BatchUpload />
          </ProtectedLayout>
        }
      />
      <Route
        path="/app/analytics"
        element={
          <ProtectedLayout>
            <Analytics />
          </ProtectedLayout>
        }
      />
    </Routes>
  )
}
