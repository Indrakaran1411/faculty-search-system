const API_BASE = "http://localhost:8000"

export async function fetchFaculty(name, affiliation = "", researchArea = "", limit = 8) {
  const params = new URLSearchParams({ name: name.trim(), limit: String(limit) })
  if (affiliation?.trim()) params.append("affiliation", affiliation.trim())
  if (researchArea?.trim()) params.append("research_area", researchArea.trim())

  const res = await fetch(`${API_BASE}/search?${params}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}
