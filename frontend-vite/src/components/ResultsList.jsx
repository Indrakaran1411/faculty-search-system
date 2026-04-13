import React from "react"
import ProfileCard, { SourceTag } from "./ProfileCard"

export default function ResultsList({ results, searchTime }) {
  if (!results) return null
  return (
    <div className="results-section">
      <div className="results-meta">
        <span className="results-count">
          {results.count} profile{results.count !== 1 ? "s" : ""} found for{" "}
          <strong>"{results.query.name}"</strong>
        </span>
        <span className="badge-pill results-scope">🌐 Worldwide sources</span>
        {results.memory_fallback && <span className="badge-pill results-memory">💾 From memory</span>}
        {results.enrichment_status === "pending" && <span className="badge-pill results-enriching">⚡ Enriching…</span>}
        {searchTime && <span className="badge-pill search-time">⚡ {searchTime}s</span>}
        <div className="sources-legend">
          Sources: <SourceTag source="google_scholar" />
          <SourceTag source="semantic_scholar" />
          <SourceTag source="orcid" />
          <SourceTag source="openalex" />
        </div>
      </div>
      <div className="results-grid">
        {results.profiles.map((profile, i) => (
          <ProfileCard key={i} profile={profile} rank={i + 1} />
        ))}
      </div>
    </div>
  )
}
