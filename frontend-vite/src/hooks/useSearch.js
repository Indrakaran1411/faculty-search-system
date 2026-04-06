import { useState, useCallback } from "react"
import { fetchFaculty } from "../utils/api"

export default function useSearch() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchTime, setSearchTime] = useState(null)

  const search = useCallback(async (name, affiliation, researchArea) => {
    if (!name?.trim()) return
    setLoading(true)
    setError(null)
    setResults(null)
    const t0 = performance.now()
    try {
      const data = await fetchFaculty(name, affiliation, researchArea)
      setResults(data)
      setSearchTime(((performance.now() - t0) / 1000).toFixed(2))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { results, loading, error, searchTime, search }
}
