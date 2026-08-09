export default function LoadingState({ text = 'Loading...', size = 'md' }) {
  const sizeMap = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-[3px]',
    lg: 'w-12 h-12 border-4',
  }

  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <div
        className={`${sizeMap[size]} border-slate-200 dark:border-slate-700 border-t-primary-500 rounded-full animate-spin`}
        role="status"
        aria-label={text}
      />
      {text && <p className="text-sm text-slate-500 dark:text-slate-400">{text}</p>}
    </div>
  )
}
