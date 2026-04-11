import { useState, useCallback, useRef } from "react"
import { fetchFaculty, fetchSearchStatus } from "../utils/api"

export default function useSearch() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchTime, setSearchTime] = useState(null)
  const pollTokenRef = useRef(0)

  const search = useCallback(async (name, affiliation, researchArea) => {
    if (!name?.trim()) return
    pollTokenRef.current += 1
    const pollToken = pollTokenRef.current
    setLoading(true)
    setError(null)
    setResults(null)
    const t0 = performance.now()
    try {
      const data = await fetchFaculty(name, affiliation, researchArea)
      setResults(data)
      setSearchTime(((performance.now() - t0) / 1000).toFixed(2))
      setLoading(false)

      if (data.search_id && data.enrichment_status === "pending") {
        for (let attempt = 0; attempt < 8; attempt += 1) {
          if (pollTokenRef.current !== pollToken) return
          await new Promise(resolve => setTimeout(resolve, 1500))
          const updated = await fetchSearchStatus(data.search_id).catch(() => null)
          if (!updated || pollTokenRef.current !== pollToken) return
          setResults(updated)
          if (updated.enrichment_status !== "pending") {
            break
          }
        }
      }
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }, [])

  return { results, loading, error, searchTime, search }
}
