import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'

export default function GlassSelect({
  value,
  onChange,
  options,
  className = '',
  placeholder = '—',
  placement = 'auto',
  disabled = false,
  shape = 'pill',
}) {
  const [open, setOpen] = useState(false)
  const [dropUp, setDropUp] = useState(placement === 'top')
  const rootRef = useRef(null)
  const listId = useId()

  const selected = options.find((opt) => String(opt.value) === String(value))

  useLayoutEffect(() => {
    if (!open) return
    if (placement === 'top') {
      setDropUp(true)
      return
    }
    if (placement === 'bottom') {
      setDropUp(false)
      return
    }
    const rect = rootRef.current?.getBoundingClientRect()
    if (!rect) return
    const spaceBelow = window.innerHeight - rect.bottom
    setDropUp(spaceBelow < 220)
  }, [open, placement])

  useEffect(() => {
    function onDocClick(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false)
    }
    function onKey(event) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [])

  return (
    <div ref={rootRef} className={`relative z-20 ${open ? 'z-[90]' : ''} ${className}`}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        disabled={disabled}
        onClick={() => {
          if (!disabled) setOpen((prev) => !prev)
        }}
        className={`flex h-10 w-full min-w-[4.5rem] items-center justify-between gap-2 border border-white/60 bg-white/10 px-3 text-sm text-white outline-none backdrop-blur-sm transition hover:bg-white/15 focus:border-white focus:ring-2 focus:ring-white/20 disabled:cursor-not-allowed disabled:opacity-50 ${
          shape === 'field' ? 'rounded-xl' : 'rounded-full'
        }`}
      >
        <span className="truncate">{selected ? selected.label : placeholder}</span>
        <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0 opacity-80" fill="none" aria-hidden>
          <path d="M5 7.5 10 12.5 15 7.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      </button>

      {open ? (
        <ul
          id={listId}
          role="listbox"
          className={`absolute inset-x-0 z-[100] max-h-52 w-full min-w-[12rem] overflow-auto rounded-2xl border border-white/35 bg-[#4c1d95]/95 p-1.5 shadow-[0_24px_60px_-16px_rgba(30,0,80,0.9)] backdrop-blur-xl ${
            dropUp ? 'bottom-[calc(100%+0.5rem)]' : 'top-[calc(100%+0.5rem)]'
          }`}
        >
          {options.map((opt) => {
            const active = String(opt.value) === String(value)
            return (
              <li key={String(opt.value)}>
                <button
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => {
                    onChange(opt.value)
                    setOpen(false)
                  }}
                  className={`flex w-full rounded-xl px-3 py-2.5 text-start text-sm transition ${
                    active
                      ? 'bg-white/25 font-semibold text-white'
                      : 'text-white/90 hover:bg-white/15'
                  }`}
                >
                  {opt.label}
                </button>
              </li>
            )
          })}
        </ul>
      ) : null}
    </div>
  )
}
