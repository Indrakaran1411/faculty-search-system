import React from "react"
import "./App.css"
import SearchPage from "./pages/SearchPage"

function Header() {
  return (
    <header className="app-header">
      <div className="header-inner">
        <div className="logo">
          <span className="logo-icon">🎓</span>
          <div>
            <h1>Faculty Search</h1>
            <p>Intelligent Academic Profile Retrieval</p>
          </div>
        </div>
        <div className="tech-tags">
          <span className="tech-tag">BM25</span>
          <span className="tech-tag">Semantic Search</span>
          <span className="tech-tag">Entity Resolution</span>
          <span className="tech-tag">Multi-Source</span>
        </div>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="app-footer">
      <span>Faculty Information Retrieval System · All free APIs · Runs locally</span>
      <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
        API Docs ↗
      </a>
    </footer>
  )
}

export default function App() {
  return (
    <div className="app">
      <Header />
      <SearchPage />
      <Footer />
    </div>
  )
}
