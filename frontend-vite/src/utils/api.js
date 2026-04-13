const API_BASE = "http://127.0.0.1:8000"

export async function fetchFaculty(name, affiliation = "", researchArea = "", limit = 20) {
  const params = new URLSearchParams({ name: name.trim(), limit: String(limit) })
  if (affiliation?.trim()) params.append("affiliation", affiliation.trim())
  if (researchArea?.trim()) params.append("research_area", researchArea.trim())

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 20000)
  let res
  try {
    res = await fetch(`${API_BASE}/search?${params}`, { signal: controller.signal })
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Search is taking too long. Try again or narrow by university.")
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchSearchStatus(searchId) {
  const res = await fetch(`${API_BASE}/search/status?search_id=${encodeURIComponent(searchId)}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchSummarize(profile) {
  const res = await fetch(`${API_BASE}/ai/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchAsk(profile, question) {
  const res = await fetch(`${API_BASE}/ai/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, question }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}
