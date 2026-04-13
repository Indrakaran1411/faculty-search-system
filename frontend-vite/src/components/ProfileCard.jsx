import React, { useState } from "react"
import AIBox from "./AIBox"

// ── Icons ───────────────────────────────────────────────────────
const Icon = ({ d, size = 13 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d={d} strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)
const EmailIcon    = () => <Icon d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6l-10 7L2 6" />
const PhoneIcon    = () => <Icon d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.35 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.6a16 16 0 0 0 6.29 6.29l.94-.94a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
const LocationIcon = () => <Icon d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z M12 10m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0" />
const LinkIcon     = () => <Icon d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6 M15 3h6v6 M10 14L21 3" />
const BookIcon     = () => <Icon d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M4 19.5A2.5 2.5 0 0 1 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15z" />
const ScholarIcon  = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z"/>
  </svg>
)
const OrcidIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zM7.369 4.378c.525 0 .947.431.947.947s-.422.947-.947.947a.95.95 0 0 1-.947-.947c0-.525.422-.947.947-.947zm-.722 3.038h1.444v10.041H6.647V7.416zm3.562 0h3.9c3.712 0 5.344 2.653 5.344 5.025 0 2.578-2.016 5.025-5.325 5.025h-3.919V7.416zm1.444 1.303v7.444h2.297c3.272 0 3.916-2.484 3.916-3.722 0-2.016-1.266-3.722-3.916-3.722h-2.297z"/>
  </svg>
)
const ChevronDown = () => <Icon d="M6 9l6 6 6-6" size={14} />
const ChevronUp   = () => <Icon d="M18 15l-6-6-6 6" size={14} />

// ── Helpers ─────────────────────────────────────────────────────
export const SourceTag = ({ source }) => {
  const labels = { google_scholar: "Scholar", orcid: "ORCID", openalex: "OpenAlex", semantic_scholar: "Sem. Scholar" }
  return <span className={`source-tag source-${source}`}>{labels[source] || source}</span>
}

const MetricBadge = ({ label, value }) =>
  value > 0 ? (
    <div className="metric-badge">
      <span className="metric-value">{value.toLocaleString()}</span>
      <span className="metric-label">{label}</span>
    </div>
  ) : null

// A field row — always rendered, shows "—" when no data
const FieldRow = ({ icon, label, value, href, mono, highlight }) => (
  <div className="info-row">
    {icon && <span className="info-icon">{icon}</span>}
    <span className="info-label">{label}</span>
    {href && value
      ? <a href={href} target="_blank" rel="noopener noreferrer" className="info-value link">{value}</a>
      : <span className={`info-value${mono ? " mono" : ""}${highlight ? " highlight" : ""}${!value ? " info-empty" : ""}`}>
          {value || "—"}
        </span>
    }
  </div>
)

// ── Main ProfileCard ─────────────────────────────────────────────
export default function ProfileCard({ profile, rank }) {
  const [pubsExpanded, setPubsExpanded] = useState(false)
  const m = profile.metrics || {}

  const initials = profile.name
    ? profile.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()
    : "??"

  const hasMetrics = Object.values(m).some(v => v > 0)
  const pubs = profile.publications || []
  const visiblePubs = pubsExpanded ? pubs.slice(0, 15) : pubs.slice(0, 3)
  const academicProfiles = profile.academic_profiles || {}
  const hasAcademicProfiles = Object.keys(academicProfiles).length > 0

  return (
    <div className="profile-card">

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
          <div className="profile-meta-row">
            {profile.designation && <span className="profile-badge designation-badge">{profile.designation}</span>}
            {profile.university  && <span className="profile-badge university-badge">{profile.university}</span>}
            {profile.department  && <span className="profile-badge dept-badge">{profile.department}</span>}
          </div>
        </div>

        <div className="sources-mini">
          {(profile.sources || []).filter(Boolean).map((src, i) => <SourceTag key={i} source={src} />)}
        </div>
      </div>

      {/* ── QUICK STATS ── */}
      {hasMetrics && (
        <div className="metrics-row">
          <MetricBadge label="Citations"  value={m.citations} />
          <MetricBadge label="h-index"    value={m.h_index} />
          <MetricBadge label="i10-index"  value={m.i10_index} />
          <MetricBadge label="Papers"     value={m.paper_count} />
        </div>
      )}

      {/* ── STRUCTURED PROFILE FIELDS ── */}
      <div className="profile-fields-grid">

        {/* Left column: Contact & Location */}
        <div className="fields-col">
          <div className="fields-section-title">📍 Contact & Location</div>
          <div className="details-list">
            <FieldRow label="University"   value={profile.university} />
            <FieldRow label="Department"   value={profile.department} />
            <FieldRow label="Location"     value={profile.location}   icon={<LocationIcon />} />
            <FieldRow label="Email"
              value={profile.email}
              href={profile.email ? `mailto:${profile.email}` : undefined}
              icon={<EmailIcon />}
            />
            <FieldRow label="Phone"  value={profile.phone} icon={<PhoneIcon />} mono />
            {profile.homepage && (
              <FieldRow label="Homepage" value={profile.homepage} href={profile.homepage} icon={<LinkIcon />} />
            )}
          </div>
        </div>

        {/* Right column: Research Areas */}
        <div className="fields-col">
          <div className="fields-section-title">🔬 Research Areas</div>
          {profile.research_areas?.length > 0 ? (
            <div className="tag-row">
              {profile.research_areas.map((area, i) => (
                <span key={i} className="area-tag">{area}</span>
              ))}
            </div>
          ) : (
            <p className="info-empty fields-empty-note">No research areas data available</p>
          )}

          {profile.affiliations?.length > 0 && (
            <>
              <div className="fields-section-title" style={{ marginTop: "0.75rem" }}>🏛 Affiliations</div>
              <div className="tag-row">
                {profile.affiliations.map((a, i) => <span key={i} className="affil-tag">{a}</span>)}
              </div>
            </>
          )}

          {profile.course_works?.length > 0 && (
            <>
              <div className="fields-section-title" style={{ marginTop: "0.75rem" }}>📖 Courses Taught</div>
              <div className="tag-row">
                {profile.course_works.map((c, i) => <span key={i} className="course-tag">{c}</span>)}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── ACADEMIC PROFILE LINKS ── */}
      <div className="section-block">
        <div className="fields-section-title">🔗 Academic Profiles</div>
        {hasAcademicProfiles ? (
          <div className="profile-links">
            {academicProfiles.google_scholar && (
              <a href={academicProfiles.google_scholar} target="_blank" rel="noopener noreferrer" className="profile-link scholar-link">
                <ScholarIcon /> Google Scholar
              </a>
            )}
            {academicProfiles.orcid && (
              <a href={academicProfiles.orcid} target="_blank" rel="noopener noreferrer" className="profile-link orcid-link">
                <OrcidIcon /> ORCID
              </a>
            )}
            {academicProfiles.openalex && (
              <a href={academicProfiles.openalex} target="_blank" rel="noopener noreferrer" className="profile-link openalex-link">
                <LinkIcon /> OpenAlex
              </a>
            )}
            {academicProfiles.semantic_scholar && (
              <a href={academicProfiles.semantic_scholar} target="_blank" rel="noopener noreferrer" className="profile-link semsch-link">
                <LinkIcon /> Sem. Scholar
              </a>
            )}
          </div>
        ) : (
          <p className="info-empty fields-empty-note">No academic profile links available</p>
        )}
      </div>

      {/* ── AI BOX ── */}
      <AIBox profile={profile} />

      {/* ── PUBLICATIONS ── */}
      <div className="section-block">
        <div className="pub-section-header">
          <div className="fields-section-title" style={{ margin: 0 }}>
            <BookIcon size={13} /> &nbsp;Publications
            {pubs.length > 0 && <span className="pub-count-badge">{pubs.length}</span>}
          </div>
          {pubs.length > 3 && (
            <button className="pub-toggle-btn" onClick={() => setPubsExpanded(e => !e)}>
              {pubsExpanded ? <><ChevronUp /> Show less</> : <><ChevronDown /> Show all {pubs.length}</>}
            </button>
          )}
        </div>

        {pubs.length > 0 ? (
          <ul className="pub-list">
            {visiblePubs.map((pub, i) => (
              <li key={i} className="pub-item">
                <span className="pub-title">{pub.title}</span>
                <div className="pub-meta">
                  {pub.year    && <span className="pub-year">{pub.year}</span>}
                  {pub.venue   && <span className="pub-venue">{pub.venue}</span>}
                  {pub.citations > 0 && <span className="pub-citations">⭐ {pub.citations.toLocaleString()} cited</span>}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="info-empty fields-empty-note">No publications data available</p>
        )}
      </div>

      {/* ── FOOTER: Relevance ── */}
      {profile.relevance_score > 0 && (
        <div className="card-footer-row">
          <span className="relevance-score">Relevance: {(profile.relevance_score * 1000).toFixed(1)}</span>
        </div>
      )}
    </div>
  )
}
