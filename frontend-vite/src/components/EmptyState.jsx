import React from "react"

const EXAMPLES = ["Andrew Ng", "Yoshua Bengio", "Geoffrey Hinton", "Fei-Fei Li"]

export default function EmptyState({ onExample }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">🔍</div>
      <h3>Search for any faculty member</h3>
      <p>
        Pulls data from Google Scholar, ORCID, OpenAlex &amp; Semantic Scholar.<br />
        All free, all local — no API keys needed.
      </p>
      <div className="example-queries">
        <span>Try:</span>
        {EXAMPLES.map((name) => (
          <button key={name} className="example-btn" onClick={() => onExample(name)}>
            {name}
          </button>
        ))}
      </div>
    </div>
  )
}
