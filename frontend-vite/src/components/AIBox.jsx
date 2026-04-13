import React, { useState, useEffect, useRef } from "react"
import { fetchAsk } from "../utils/api"

// Typing animation hook
function useTypewriter(text, speed = 18) {
  const [displayed, setDisplayed] = useState("")
  useEffect(() => {
    if (!text) { setDisplayed(""); return }
    setDisplayed("")
    let i = 0
    const interval = setInterval(() => {
      i += 1
      setDisplayed(text.slice(0, i))
      if (i >= text.length) clearInterval(interval)
    }, speed)
    return () => clearInterval(interval)
  }, [text, speed])
  return displayed
}

// Sparkle SVG
const SparkleIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 2l2.09 6.26L20 10l-5.91 1.74L12 18l-2.09-6.26L4 10l5.91-1.74L12 2z" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const SendIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
)

const BotIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    <line x1="12" y1="3" x2="12" y2="7"/>
    <line x1="8" y1="18" x2="8" y2="18"/>
    <line x1="16" y1="18" x2="16" y2="18"/>
  </svg>
)

// Format answer text with **bold** support
function FormattedText({ text }) {
  if (!text) return null
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <span>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**")
          ? <strong key={i}>{part.slice(2, -2)}</strong>
          : <span key={i}>{part}</span>
      )}
    </span>
  )
}

// AI Summary panel with typewriter effect
function AISummary({ profile }) {
  const summary = profile.research_summary || ""
  const displayed = useTypewriter(summary, 14)

  if (!summary) return null

  return (
    <div className="ai-summary-box">
      <div className="ai-summary-header">
        <SparkleIcon />
        <span>AI Research Summary</span>
        <span className="ai-badge">AI Generated</span>
      </div>
      <p className="ai-summary-text">
        {displayed}
        <span className="ai-cursor" aria-hidden="true" />
      </p>
    </div>
  )
}

// Suggested questions
const SUGGESTED_QUESTIONS = [
  "What does this professor research?",
  "How many citations do they have?",
  "Where do they work?",
  "What courses do they teach?",
]

// QA Chat panel
function AIChat({ profile }) {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState("")
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const inputRef = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  const ask = async (q) => {
    const query = (q || question).trim()
    if (!query || loading) return
    setQuestion("")
    setMessages(prev => [...prev, { role: "user", text: query }])
    setLoading(true)
    try {
      const data = await fetchAsk(profile, query)
      setMessages(prev => [...prev, { role: "ai", text: data.answer }])
    } catch {
      setMessages(prev => [...prev, { role: "ai", text: "Sorry, I couldn't retrieve an answer. Make sure the backend is running.", error: true }])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask() }
  }

  return (
    <div className="ai-chat-container">
      <button className="ai-chat-toggle" onClick={() => setOpen(o => !o)}>
        <BotIcon />
        <span>Ask AI about {profile.name?.split(" ")[0] || "this professor"}</span>
        <span className="ai-chat-arrow">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="ai-chat-panel">
          {messages.length === 0 && (
            <div className="ai-chat-suggestions">
              <div className="ai-suggestions-label">Suggested questions:</div>
              <div className="ai-suggestions-grid">
                {SUGGESTED_QUESTIONS.map(q => (
                  <button key={q} className="ai-suggestion-btn" onClick={() => ask(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="ai-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`ai-message ai-message-${msg.role} ${msg.error ? "ai-message-error" : ""}`}>
                {msg.role === "ai" && (
                  <div className="ai-message-icon"><BotIcon /></div>
                )}
                <div className="ai-message-bubble">
                  <FormattedText text={msg.text} />
                </div>
              </div>
            ))}
            {loading && (
              <div className="ai-message ai-message-ai">
                <div className="ai-message-icon"><BotIcon /></div>
                <div className="ai-message-bubble ai-thinking">
                  <span className="ai-dot" /><span className="ai-dot" /><span className="ai-dot" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="ai-chat-input-row">
            <input
              ref={inputRef}
              className="ai-chat-input"
              placeholder={`Ask anything about ${profile.name?.split(" ")[0] || "this professor"}…`}
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
            />
            <button
              className="ai-chat-send"
              onClick={() => ask()}
              disabled={!question.trim() || loading}
              aria-label="Send question"
            >
              <SendIcon />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Main export
export default function AIBox({ profile }) {
  const hasSummary = !!profile.research_summary
  const hasEnoughData = !!(
    profile.name && (
      profile.research_areas?.length ||
      profile.publications?.length ||
      profile.metrics?.citations > 0
    )
  )
  if (!hasEnoughData) return null

  return (
    <div className="ai-box">
      {hasSummary && <AISummary profile={profile} />}
      <AIChat profile={profile} />
    </div>
  )
}
