import React, { useState } from "react"

// ── Icons ──────────────────────────────────────────────────────────
const Icon = ({ d, size = 13 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d={d} strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)
const EmailIcon    = () => <Icon d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6l-10 7L2 6" />
const PhoneIcon    = () => <Icon d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.35 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.6a16 16 0 0 0 6.29 6.29l.94-.94a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
const LocationIcon = () => <Icon d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z M12 10m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0" />
const LinkIcon     = () => <Icon d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6 M15 3h6v6 M10 14L21 3" />
const ScholarIcon  = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z"/>
  </svg>
)

const formatList = (items) => (items?.filter(Boolean)?.length ? items.join(", ") : "Not available")
const formatPublications = (publications) => {
  if (!publications?.length) return "Not available"
  return publications
    .slice(0, 8)
    .map((pub) => [pub.title, pub.year ? `(${pub.year})` : ""].filter(Boolean).join(" "))
    .join("; ")
}

// ── Source Tag ──────────────────────────────────────────────────────
export const SourceTag = ({ source }) => {
  const labels = { google_scholar: "Scholar", orcid: "ORCID", openalex: "OpenAlex", semantic_scholar: "Sem. Scholar" }
  return <span className={`source-tag source-${source}`}>{labels[source] || source}</span>
}

// ── Metric Badge ────────────────────────────────────────────────────
const MetricBadge = ({ label, value }) =>
  value > 0 ? (
    <div className="metric-badge">
      <span className="metric-value">{value.toLocaleString()}</span>
      <span className="metric-label">{label}</span>
    </div>
  ) : null

// ── Info Row ────────────────────────────────────────────────────────
const InfoRow = ({ icon, label, value, href }) => {
  if (!value) return null
  return (
    <div className="info-row">
      <span className="info-icon">{icon}</span>
      <span className="info-label">{label}</span>
      {href
        ? <a href={href} target="_blank" rel="noopener noreferrer" className="info-value link">{value}</a>
        : <span className="info-value">{value}</span>
      }
    </div>
  )
}

// ── Section ─────────────────────────────────────────────────────────
const Section = ({ title, children }) => (
  <div className="card-section">
    <div className="section-title">{title}</div>
    {children}
  </div>
)

// ── Main ProfileCard ─────────────────────────────────────────────────
export default function ProfileCard({ profile, rank }) {
  const [expanded, setExpanded] = useState(false)
  const m = profile.metrics || {}
  const initials = profile.name
    ? profile.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()
    : "??"

  const hasMetrics = Object.values(m).some(v => v > 0)

  return (
    <div className={`profile-card ${expanded ? "expanded" : ""}`}>

      {/* ── TOP HEADER ── */}
      <div className="card-header">
        <div className="rank-badge">#{rank}</div>

        <div className="avatar">
          {profile.profile_image && (
            <img src={profile.profile_image} alt={profile.name}
              onError={e => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex" }} />
          )}
          <div className="avatar-initials" style={{ display: profile.profile_image ? "none" : "flex" }}>
            {initials}
          </div>
        </div>

        <div className="profile-main">
          <h2 className="profile-name">{profile.name || "Unknown"}</h2>
          <div className="profile-summary">
            Search results are aggregated from worldwide academic sources.
          </div>
        </div>

        <button className="expand-btn" onClick={() => setExpanded(!expanded)}>
          {expanded ? "▲ Less" : "▼ More"}
        </button>
      </div>

      <div className="details-list">
        <InfoRow label="Name" value={profile.name || "Not available"} />
        <InfoRow label="Designation" value={profile.designation || "Not available"} />
        <InfoRow label="University/Clg" value={profile.university || "Not available"} />
        <InfoRow label="Department" value={profile.department || "Not available"} />
        <InfoRow label="Research areas" value={formatList(profile.research_areas)} />
        <InfoRow label="Course works" value={formatList(profile.course_works)} />
        <InfoRow label="Publications" value={formatPublications(profile.publications)} />
        <InfoRow label="Email" value={profile.email || "Not available"} href={profile.email ? `mailto:${profile.email}` : undefined} />
        <InfoRow label="Contact number" value={profile.phone || "Not available"} />
        <InfoRow label="Location" value={profile.location || "Not available"} />
      </div>

      {profile.homepage && (
        <div className="contact-strip">
          <InfoRow icon={<LinkIcon />} label="Website" value={profile.homepage} href={profile.homepage} />
        </div>
      )}

      {hasMetrics && (
        <div className="metrics-row">
          <MetricBadge label="Citations"  value={m.citations} />
          <MetricBadge label="h-index"    value={m.h_index} />
          <MetricBadge label="i10-index"  value={m.i10_index} />
          <MetricBadge label="Papers"     value={m.paper_count} />
        </div>
      )}

      {/* ── PROFILE LINKS ── */}
      {Object.keys(profile.academic_profiles || {}).length > 0 && (
        <div className="profile-links">
          {profile.academic_profiles.google_scholar && (
            <a href={profile.academic_profiles.google_scholar} target="_blank" rel="noopener noreferrer" className="profile-link scholar-link">
              <ScholarIcon /> Google Scholar
            </a>
          )}
          {profile.academic_profiles.orcid && (
            <a href={profile.academic_profiles.orcid} target="_blank" rel="noopener noreferrer" className="profile-link orcid-link">ORCID</a>
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
        </div>
      )}

      {/* ── EXPANDED CONTENT ── */}
      {expanded && (
        <>
          {profile.publications?.length > 0 && (
            <Section title="📄 Publications">
              <ul className="pub-list">
                {profile.publications.slice(0, 10).map((pub, i) => (
                  <li key={i} className="pub-item">
                    <span className="pub-title">{pub.title}</span>
                    <div className="pub-meta">
                      {pub.year    && <span className="pub-year">{pub.year}</span>}
                      {pub.venue   && <span className="pub-venue">{pub.venue}</span>}
                      {pub.citations > 0 && <span className="pub-citations">⭐ {pub.citations} cited</span>}
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </>
      )}

      {/* ── SOURCES ── */}
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
