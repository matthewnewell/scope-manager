import { Route, Routes } from 'react-router-dom'
import Nav from './components/Nav'
import SplashPage from './pages/SplashPage'
import ScopeTreePage from './pages/ScopeTreePage'
import ScopeItemDetailPage from './pages/ScopeItemDetailPage'
import './App.css'

/** Shared chrome for every operational page — same pattern as the sibling apps: the splash
 * page renders its own Nav directly, everything else gets it via this layout. */
function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <Nav />
      <div className="app-layout__body">{children}</div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/about" element={<SplashPage />} />
      <Route path="/" element={<Layout><ScopeTreePage /></Layout>} />
      <Route path="/items/:itemId" element={<Layout><ScopeItemDetailPage /></Layout>} />
    </Routes>
  )
}
