import React, { useState, useCallback } from "react"
import SearchBar from "../components/SearchBar"
import ResultsList from "../components/ResultsList"
import EmptyState from "../components/EmptyState"
import useSearch from "../hooks/useSearch"

export default function SearchPage() {
  const [query, setQuery] = useState("")
  const [affiliation, setAffiliation] = useState("")
  const [researchArea, setResearchArea] = useState("")
  const { results, loading, error, searchTime, search } = useSearch()

  const handleSearch = useCallback(() => {
    search(query, affiliation, researchArea)
  }, [query, affiliation, researchArea, search])

  const handleExample = useCallback((name) => {
    setQuery(name)
    setAffiliation("")
    setResearchArea("")
    search(name, "", "")
  }, [search])

  return (
    <main className="app-main">
      <SearchBar
        query={query} setQuery={setQuery}
        affiliation={affiliation} setAffiliation={setAffiliation}
        researchArea={researchArea} setResearchArea={setResearchArea}
        onSearch={handleSearch} loading={loading}
      />
      {error && (
        <div className="error-box">
          <strong>⚠ Error:</strong> {error}
          <p style={{ marginTop: "0.4rem", fontSize: "0.82rem", opacity: 0.8 }}>
            Make sure the backend is running: <code>cd backend && python main.py</code>
          </p>
        </div>
      )}
      {results && <ResultsList results={results} searchTime={searchTime} />}
      {!results && !loading && !error && <EmptyState onExample={handleExample} />}
    </main>
  )
}
