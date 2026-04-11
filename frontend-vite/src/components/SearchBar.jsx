import React from "react"

const SearchIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
  </svg>
)

export default function SearchBar({ query, setQuery, affiliation, setAffiliation, researchArea, setResearchArea, onSearch, loading }) {
  const handleKey = (e) => { if (e.key === "Enter") onSearch() }

  return (
    <div className="search-box">
      <div className="search-primary">
        <SearchIcon />
        <input
          className="search-input"
          type="text"
          placeholder="Professor name (global search, e.g. Andrew Ng, Geoffrey Hinton)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          autoFocus
        />
      </div>
      <div className="search-filters">
        <input
          className="filter-input"
          type="text"
          placeholder="University / Institution (optional)"
          value={affiliation}
          onChange={(e) => setAffiliation(e.target.value)}
          onKeyDown={handleKey}
        />
        <input
          className="filter-input"
          type="text"
          placeholder="Research area (optional)"
          value={researchArea}
          onChange={(e) => setResearchArea(e.target.value)}
          onKeyDown={handleKey}
        />
      </div>
      <button
        className={`search-btn ${loading ? "loading" : ""}`}
        onClick={onSearch}
        disabled={loading || !query.trim()}
      >
        {loading ? <span className="spinner" /> : <SearchIcon />}
        {loading ? "Searching..." : "Search Professor"}
      </button>
    </div>
  )
}
