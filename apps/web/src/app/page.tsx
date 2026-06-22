import Link from "next/link";

const FEATURES = [
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
      </svg>
    ),
    title: "Correct Answer Keys",
    body: "Every answer is computed by SymPy — a computer algebra system — and verified before it ever reaches your worksheet. No typos, no guesses.",
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5 10.5 6.75l3 3 2.25-2.25L19.5 12M3.75 20.25h16.5" />
      </svg>
    ),
    title: "Step-by-Step Solutions",
    body: "AI-generated worked solutions written toward the known correct answer. Great for self-paced learners and substitute teachers.",
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9z" />
      </svg>
    ),
    title: "Clean PDF Export",
    body: "Print-ready output with proper work spacing, readable equations, and a name / date / period header. Kuta-quality formatting, minus the subscription.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white font-[family-name:var(--font-geist-sans)]">
      {/* ── Nav ── */}
      <header className="sticky top-0 z-20 border-b border-gray-100 bg-white/90 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <span className="text-xl font-bold tracking-tight text-gray-900">
            Exam<span className="text-indigo-600">Target</span>
          </span>
          <nav className="flex items-center gap-4">
            <Link
              href="/sign-in"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/builder"
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 transition-colors"
            >
              Go to Builder
            </Link>
          </nav>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="mx-auto max-w-4xl px-6 pb-24 pt-20 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3.5 py-1.5 text-xs font-semibold text-indigo-700">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
          Every answer verified by SymPy
        </div>

        <h1 className="mx-auto max-w-2xl text-5xl font-bold tracking-tight text-gray-900 sm:text-6xl">
          Math Worksheets with{" "}
          <span className="text-indigo-600">Verified Answer Keys</span>
        </h1>

        <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-gray-500">
          For teachers and homeschool parents. Every answer machine-verified by
          SymPy — no typos, no miskeys, just correct math ready to print.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/builder"
            className="w-full rounded-xl bg-indigo-600 px-8 py-3.5 text-base font-semibold text-white shadow-md hover:bg-indigo-500 transition-colors sm:w-auto"
          >
            Start Building Free
          </Link>
          <Link
            href="/sign-in"
            className="w-full rounded-xl border border-gray-200 bg-white px-8 py-3.5 text-base font-semibold text-gray-700 hover:bg-gray-50 transition-colors sm:w-auto"
          >
            Sign in
          </Link>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="border-t border-gray-100 bg-gray-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">
              Everything a math teacher actually needs
            </h2>
            <p className="mt-3 text-base text-gray-500">
              Built for the classroom, not the demo.
            </p>
          </div>

          <div className="grid gap-8 sm:grid-cols-3">
            {FEATURES.map(({ icon, title, body }) => (
              <div
                key={title}
                className="rounded-2xl border border-gray-200 bg-white p-7 shadow-xs"
              >
                <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  {icon}
                </div>
                <h3 className="mb-2 text-base font-semibold text-gray-900">
                  {title}
                </h3>
                <p className="text-sm leading-relaxed text-gray-500">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-20">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900">
            Ready to build your first worksheet?
          </h2>
          <p className="mt-4 text-base text-gray-500">
            Free to start. No credit card required.
          </p>
          <Link
            href="/builder"
            className="mt-8 inline-block rounded-xl bg-indigo-600 px-10 py-4 text-base font-semibold text-white shadow-md hover:bg-indigo-500 transition-colors"
          >
            Open the Builder
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-gray-100 py-8">
        <div className="mx-auto max-w-6xl px-6 text-center text-xs text-gray-400">
          © {new Date().getFullYear()} ExamTarget. Built for teachers.
        </div>
      </footer>
    </div>
  );
}
