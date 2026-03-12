export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50">
      {/* Header */}
      <header className="border-b border-zinc-800">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
              <svg
                className="h-5 w-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
                />
              </svg>
            </div>
            <h1 className="text-lg font-semibold tracking-tight">
              Meta Ads Bulk Uploader
            </h1>
          </div>
          <nav className="flex items-center gap-4">
            <a
              href="#"
              className="rounded-md px-3 py-2 text-sm text-zinc-400 transition-colors hover:text-zinc-100"
            >
              Campaigns
            </a>
            <a
              href="#"
              className="rounded-md px-3 py-2 text-sm text-zinc-400 transition-colors hover:text-zinc-100"
            >
              Upload
            </a>
            <a
              href="#"
              className="rounded-md px-3 py-2 text-sm text-zinc-400 transition-colors hover:text-zinc-100"
            >
              History
            </a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="mx-auto max-w-7xl px-6 py-20">
        <div className="text-center">
          <h2 className="text-4xl font-bold tracking-tight text-zinc-50 sm:text-5xl">
            Bulk upload ads to Meta
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-zinc-400">
            Stop creating Facebook and Instagram ads one by one. Upload dozens
            of creatives at once through Meta&apos;s Marketing API and launch
            campaigns in minutes, not hours.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <button className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500">
              Start Uploading
            </button>
            <button className="rounded-lg border border-zinc-700 bg-zinc-900 px-5 py-2.5 text-sm font-medium text-zinc-300 transition-colors hover:border-zinc-600 hover:text-zinc-100">
              View Documentation
            </button>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="mt-20 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
              <svg
                className="h-5 w-5 text-blue-500"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
                />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-zinc-100">
              Bulk CSV Upload
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-zinc-400">
              Upload a CSV with ad copy, targeting, budgets, and creative
              assets. We handle the rest via Meta&apos;s Marketing API.
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
              <svg
                className="h-5 w-5 text-blue-500"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-zinc-100">
              Validation &amp; Preview
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-zinc-400">
              Every ad is validated against Meta&apos;s specs before submission.
              Preview how your ads will look before going live.
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
              <svg
                className="h-5 w-5 text-blue-500"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"
                />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-zinc-100">
              Campaign Analytics
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-zinc-400">
              Track upload history, monitor ad status, and view performance
              metrics — all from one dashboard.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <p className="text-center text-sm text-zinc-500">
            Meta Ads Bulk Uploader &mdash; Built for media buyers who move fast.
          </p>
        </div>
      </footer>
    </div>
  );
}
