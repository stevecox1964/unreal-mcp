import { useEffect, useRef, useState } from 'react'
import * as api from '../api'

export default function LogPanel() {
  const [content, setContent] = useState('')
  const [confirming, setConfirming] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const load = () => api.getLog().then(setContent).catch(() => {})

  useEffect(() => {
    load()
    const id = setInterval(load, 2000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const el = textareaRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [content])

  const handleDelete = async () => {
    if (confirming) {
      await api.deleteLog()
      setContent('')
      setConfirming(false)
    } else {
      setConfirming(true)
      setTimeout(() => setConfirming(false), 3000)
    }
  }

  return (
    <div className="log-panel">
      <div className="log-header">
        <span className="log-title">UNREAL LOG</span>
        <button
          className={`btn btn-sm ${confirming ? 'btn-danger' : 'btn-secondary'}`}
          onClick={handleDelete}
        >
          {confirming ? 'Confirm delete?' : 'Delete log'}
        </button>
      </div>
      <textarea
        ref={textareaRef}
        className="log-area"
        readOnly
        value={content || '— no log file —'}
      />
    </div>
  )
}
