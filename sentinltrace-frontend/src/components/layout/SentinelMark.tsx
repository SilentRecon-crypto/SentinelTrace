export function SentinelMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M16 5 L26 9 V16 C26 22 21.5 26.5 16 28 C10.5 26.5 6 22 6 16 V9 Z"
        stroke="var(--color-signal)"
        strokeWidth="1.6"
      />
      <circle cx="16" cy="15" r="2.4" fill="var(--color-signal)" />
      <path d="M16 15 L21 11 M16 15 L12 20" stroke="var(--color-signal)" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="21" cy="11" r="1.3" fill="var(--color-high)" />
      <circle cx="12" cy="20" r="1.3" fill="var(--color-critical)" />
    </svg>
  );
}
