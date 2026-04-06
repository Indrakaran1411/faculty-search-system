import React, { useState } from "react"

const EmailIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
    <polyline points="22,6 12,13 2,6"/>
  </svg>
)
const BookIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
  </svg>
)
const LinkIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
    <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
  </svg>
)
const ScholarIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z"/>
  </svg>
)

const MetricBadge = ({ label, value }) =>
  value > 0 ? (
    <div className="metric-badge">
      <span className="metric-value">{value.toLocaleString()}</span>
      <span className="metric-label">{label}</span>
    </div>
  ) : null

export const SourceTag = ({ source }) => {
  const labels = { google_scholar: "Scholar", orcid: "ORCID", openalex: "OpenAlex", semantic_scholar: "Sem. Scholar" }
  return <span className={`source-tag source-${source}`}>{labels[source] || source}</span>
}

export default function ProfileCard({ profile, rank }) {
  const [expanded, setExpanded] = useState(false)
  const m = profile.metrics || {}
  const initials = profile.name
    ? profile.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
    : "??"

  return (
    <div className={`profile-card ${expanded ? "expanded" : ""}`}>
      <div className="card-header">
        <div className="rank-badge">#{rank}</div>
        <div className="avatar">
          {profile.profile_image && (
            <img src={profile.profile_image} alt={profile.name}
              onError={(e) => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex" }} />
          )}
          <div className="avatar-initials" style={{ display: profile.profile_image ? "none" : "flex" }}>
            {initials}
          </div>
        </div>
        <div className="profile-main">
          <h2 className="profile-name">{profile.name || "Unknown"}</h2>
          {profile.university && <div className="profile-university">🏛 {profile.university}</div>}
          {profile.department && <div className="profile-dept">{profile.department}</div>}
          {profile.email && (
            <a href={`mailto:${profile.email}`} className="profile-email">
              <EmailIcon /> {profile.email}
            </a>
          )}
        </div>
        <button className="expand-btn" onClick={() => setExpanded(!expanded)}>
          {expanded ? "▲ Less" : "▼ More"}
        </button>
      </div>

      <div className="metrics-row">
        <MetricBadge label="Citations" value={m.citations} />
        <MetricBadge label="h-index" value={m.h_index} />
        <MetricBadge label="i10-index" value={m.i10_index} />
        <MetricBadge label="Papers" value={m.paper_count} />
      </div>

      {profile.research_areas?.length > 0 && (
        <div className="research-areas">
          {profile.research_areas.slice(0, 6).map((area, i) => (
            <span key={i} className="area-tag">{area}</span>
          ))}
        </div>
      )}

      {Object.keys(profile.academic_profiles || {}).length > 0 && (
        <div className="profile-links">
          {profile.academic_profiles.google_scholar && (
            <a href={profile.academic_profiles.google_scholar} target="_blank" rel="noopener noreferrer" className="profile-link scholar-link">
              <ScholarIcon /> Google Scholar
            </a>
          )}
          {profile.academic_profiles.orcid && (
            <a href={profile.academic_profiles.orcid} target="_blank" rel="noopener noreferrer" className="profile-link orcid-link">
              ORCID
            </a>
          )}
          {profile.academic_profiles.openalex && (
            <a href={profile.academic_profiles.openalex} target="_blank" rel="noopener noreferrer" className="profile-link openalex-link">
              <LinkIcon /> OpenAlex
            </a>
          )}
          {profile.academic_profiles.semantic_scholar && (
            <a href={profile.academic_profiles.semantic_scholar} target="_blank" rel="noopener noreferrer" className="profile-link semsch-link">
              <LinkIcon /> Sem. Scholar
            </a>
          )}
          {profile.homepage && (
            <a href={profile.homepage} target="_blank" rel="noopener noreferrer" className="profile-link home-link">
              <LinkIcon /> Homepage
            </a>
          )}
        </div>
      )}

      {expanded && profile.publications?.length > 0 && (
        <div className="publications">
          <h4><BookIcon /> Top Publications</h4>
          <ul>
            {profile.publications.slice(0, 8).map((pub, i) => (
              <li key={i} className="pub-item">
                <span className="pub-title">{pub.title}</span>
                <span className="pub-meta">
                  {pub.year && <span className="pub-year">{pub.year}</span>}
                  {pub.citations > 0 && <span className="pub-citations">⭐ {pub.citations}</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="sources-row">
        {(profile.sources || []).filter(Boolean).map((src, i) => (
          <SourceTag key={i} source={src} />
        ))}
        {profile.relevance_score > 0 && (
          <span className="relevance-score">Score: {(profile.relevance_score * 1000).toFixed(1)}</span>
        )}
      </div>
    </div>
  )
}
