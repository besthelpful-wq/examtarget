"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { UserButton } from "@clerk/nextjs";
import katex from "katex";
import "katex/dist/katex.min.css";

// ─── Types ────────────────────────────────────────────────────────────────────

interface TopicInfo {
  slug: string;
  display_name: string;
  standard_codes: string[];
}

interface Step {
  description: string;
  math_latex: string;
}

interface StepSolution {
  steps: Step[];
  final_answer_latex: string;
  method: string;
  verified: boolean;
}

interface ProblemResult {
  problem_latex: string;
  answer_latex: string;
  seed_used: number;
  difficulty: string;
  standard_codes: string[];
  step_solution?: StepSolution | null;
}

interface Worksheet {
  topic: string;
  difficulty: string;
  version: number;
  seed: number;
  problems: ProblemResult[];
}

type Difficulty = "easy" | "medium" | "hard";
type StepsPlacement = "inline" | "separate_page";

const VERSION_LABELS = ["A", "B", "C", "D"] as const;
const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard"];
const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://localhost:8000";

// ─── Atoms ────────────────────────────────────────────────────────────────────

function KaTeXSpan({
  latex,
  display = false,
}: {
  latex: string;
  display?: boolean;
}) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(latex, {
        displayMode: display,
        throwOnError: false,
        output: "htmlAndMathml",
      });
    } catch {
      return `<span style="color:#dc2626">${latex}</span>`;
    }
  }, [latex, display]);
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function Toggle({
  id,
  checked,
  onChange,
  label,
  sublabel,
  disabled = false,
}: {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  sublabel?: string;
  disabled?: boolean;
}) {
  return (
    <label
      htmlFor={id}
      className={`flex items-center gap-3 ${disabled ? "cursor-not-allowed opacity-40" : "cursor-pointer"}`}
    >
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent
          transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2
          focus-visible:ring-indigo-600 focus-visible:ring-offset-2
          ${checked && !disabled ? "bg-indigo-600" : "bg-gray-200"}`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow
            transition-transform duration-200 ${checked ? "translate-x-5" : "translate-x-0"}`}
        />
      </button>
      <span className="text-sm font-medium text-gray-700">
        {label}
        {sublabel && (
          <span className="ml-1.5 text-xs font-normal text-gray-400">
            {sublabel}
          </span>
        )}
      </span>
    </label>
  );
}

function Spinner() {
  return (
    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
  );
}

// ─── Steps section (collapsible) ──────────────────────────────────────────────

function StepsSection({ solution }: { solution: StepSolution }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-3 border-t border-dashed border-gray-200 pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-indigo-500 transition-colors hover:text-indigo-700"
      >
        {/* chevron */}
        <svg
          className={`h-3 w-3 transition-transform duration-150 ${open ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {open ? "Hide" : "Show"} step-by-step solution
      </button>

      {open && (
        <ol className="mt-3 space-y-3 pl-1">
          {solution.steps.map((step, i) => (
            <li key={i} className="flex gap-3">
              <span className="mt-0.5 shrink-0 text-xs font-bold tabular-nums text-gray-400">
                {i + 1}.
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm leading-snug text-gray-600">
                  {step.description}
                </p>
                <div className="mt-1 overflow-x-auto py-0.5 text-sm">
                  <KaTeXSpan latex={step.math_latex} display />
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// ─── Problem card ─────────────────────────────────────────────────────────────

function ProblemCard({
  index,
  problem,
  showAnswer,
  showSteps,
}: {
  index: number;
  problem: ProblemResult;
  showAnswer: boolean;
  showSteps: boolean;
}) {
  return (
    <div className="group rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-xs transition-shadow hover:shadow-sm">
      <div className="flex gap-4">
        <span className="w-7 shrink-0 pt-0.5 text-sm font-semibold tabular-nums text-gray-400">
          {index + 1}.
        </span>

        <div className="min-w-0 flex-1">
          {/* Problem */}
          <div className="overflow-x-auto py-1 text-[1.05rem] leading-relaxed">
            <KaTeXSpan latex={problem.problem_latex} display />
          </div>

          {/* Answer key */}
          {showAnswer && (
            <div className="mt-3 flex items-baseline gap-2 border-t border-dashed border-gray-200 pt-3">
              <span className="shrink-0 text-[11px] font-semibold uppercase tracking-widest text-indigo-500">
                Answer
              </span>
              <span className="overflow-x-auto text-sm text-gray-700">
                <KaTeXSpan latex={problem.answer_latex} />
              </span>
            </div>
          )}

          {/* Step-by-step solution */}
          {showSteps && problem.step_solution && (
            <StepsSection solution={problem.step_solution} />
          )}

          {/* Loading placeholder when steps were requested but not yet returned */}
          {showSteps && problem.step_solution === null && (
            <div className="mt-3 border-t border-dashed border-gray-200 pt-3">
              <span className="text-xs text-gray-400 italic">
                Steps unavailable for this problem.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Section shell ────────────────────────────────────────────────────────────

function Section({
  title,
  badge,
  children,
}: {
  title: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-xs">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
        {badge}
      </div>
      {children}
    </section>
  );
}

// ─── Builder page ─────────────────────────────────────────────────────────────

export default function BuilderClient() {
  // — Step 1 state —
  const [topics, setTopics] = useState<TopicInfo[]>([]);
  const [topicsErr, setTopicsErr] = useState(false);
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("easy");
  const [count, setCount] = useState(10);
  const [multiVersion, setMultiVersion] = useState(false);
  const [versionCount, setVersionCount] = useState(2);

  // — Step 2 state —
  const [worksheets, setWorksheets] = useState<Worksheet[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [showAnswerKey, setShowAnswerKey] = useState(false);
  const [includeSteps, setIncludeSteps] = useState(false);
  const [stepsPlacement, setStepsPlacement] = useState<StepsPlacement>("inline");
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  // Saved so the steps toggle can re-fetch with the same seed
  const [lastSeed, setLastSeed] = useState<number | null>(null);
  const lastSeedRef = useRef<number | null>(null);

  const previewRef = useRef<HTMLDivElement>(null);

  // Fetch topics on mount
  useEffect(() => {
    fetch(`${ENGINE}/topics`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json() as Promise<TopicInfo[]>;
      })
      .then((data) => {
        setTopics(data);
        if (data.length) setTopic(data[0].slug);
      })
      .catch(() => setTopicsErr(true));
  }, []);

  // ─── Core fetch ─────────────────────────────────────────────────────────────

  const doFetch = useCallback(
    async (seed: number, withSteps: boolean) => {
      if (!topic) return;
      setGenerating(true);
      setGenError(null);
      setWorksheets([]);
      setLastSeed(seed);
      lastSeedRef.current = seed;

      const numVersions = multiVersion ? versionCount : 1;

      try {
        const requests = Array.from({ length: numVersions }, (_, i) =>
          fetch(`${ENGINE}/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              topic,
              difficulty,
              count,
              seed,
              version: i + 1,
              include_steps: withSteps,
            }),
          }).then(async (r) => {
            if (!r.ok) {
              const body = await r.json().catch(() => ({})) as { detail?: string };
              throw new Error(body.detail ?? `HTTP ${r.status}`);
            }
            return r.json() as Promise<Worksheet>;
          }),
        );

        const results = await Promise.all(requests);
        setWorksheets(results);
        setActiveTab(0);
        setShowAnswerKey(false);

        setTimeout(
          () => previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
          80,
        );
      } catch (e) {
        setGenError((e as Error).message);
      } finally {
        setGenerating(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [topic, difficulty, count, multiVersion, versionCount],
  );

  const handleGenerate = () => {
    const seed = (Math.random() * 100_000) | 0;
    doFetch(seed, includeSteps);
  };

  // Re-fetch with steps when the toggle turns on and we already have problems
  const handleStepsToggle = (val: boolean) => {
    setIncludeSteps(val);
    if (val && worksheets.length > 0 && lastSeedRef.current !== null) {
      doFetch(lastSeedRef.current, true);
    }
  };

  // ─── PDF export ─────────────────────────────────────────────────────────────

  const handleDownloadPDF = async () => {
    if (!current) return;
    setDownloading(true);
    setGenError(null);

    try {
      const topicLabel = topics.find((t) => t.slug === topic)?.display_name ?? topic;
      const versionSuffix =
        worksheets.length > 1 ? ` — Version ${VERSION_LABELS[activeTab]}` : "";
      const title = `${topicLabel}${versionSuffix}`;

      // Strip step_solution when not requested to keep the payload lean
      const problems = includeSteps
        ? current.problems
        : current.problems.map(({ step_solution: _s, ...rest }) => rest);

      const res = await fetch(`${ENGINE}/export/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: current.topic,
          difficulty: current.difficulty,
          seed: current.seed,
          version: current.version,
          problems,
          include_answer_key: showAnswerKey,
          include_steps: includeSteps,
          steps_placement: stepsPlacement,
          title,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = title.replace(/\s+/g, "_") + ".pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setGenError((e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  const current = worksheets[activeTab];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Nav ── */}
      <nav className="sticky top-0 z-20 border-b border-gray-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
          <a href="/" className="text-lg font-bold tracking-tight text-gray-900">
            ExamTarget
          </a>
          <UserButton />
        </div>
      </nav>

      <div className="mx-auto max-w-4xl space-y-8 px-4 py-10">
        {/* Page title */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Worksheet Builder</h1>
          <p className="mt-1 text-sm text-gray-500">
            Configure your worksheet, then click Generate to preview.
          </p>
        </div>

        {/* ══════════════════════════════════════════
            Step 1 — Configure
        ══════════════════════════════════════════ */}
        <Section title="Configure">
          <div className="space-y-6">
            {/* Topic */}
            <div className="space-y-1.5">
              <label
                htmlFor="topic"
                className="block text-sm font-medium text-gray-700"
              >
                Topic
              </label>
              {topicsErr ? (
                <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  Could not reach the engine at{" "}
                  <code className="font-mono">{ENGINE}</code>. Make sure it&apos;s
                  running.
                </p>
              ) : topics.length === 0 ? (
                <div className="h-10 animate-pulse rounded-lg bg-gray-100" />
              ) : (
                <select
                  id="topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-xs focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {topics.map((t) => (
                    <option key={t.slug} value={t.slug}>
                      {t.display_name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Difficulty */}
            <div className="space-y-2">
              <span className="block text-sm font-medium text-gray-700">
                Difficulty
              </span>
              <div className="flex gap-2">
                {DIFFICULTIES.map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDifficulty(d)}
                    className={`rounded-full px-5 py-2 text-sm font-medium transition-all ${
                      difficulty === d
                        ? "bg-indigo-600 text-white shadow-sm ring-2 ring-indigo-600 ring-offset-2"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {d[0].toUpperCase() + d.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Problem count */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  Problem Count
                </span>
                <span className="min-w-[2rem] text-right text-sm font-bold tabular-nums text-indigo-600">
                  {count}
                </span>
              </div>
              <input
                type="range"
                min={5}
                max={40}
                step={5}
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className="h-2 w-full cursor-pointer appearance-none rounded-full bg-gray-200 accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-gray-400">
                {[5, 10, 15, 20, 25, 30, 35, 40].map((n) => (
                  <span key={n}>{n}</span>
                ))}
              </div>
            </div>

            {/* Versions */}
            <div className="space-y-3">
              <Toggle
                id="multi-version"
                checked={multiVersion}
                onChange={setMultiVersion}
                label="Multiple versions (A / B / C / D)"
              />
              {multiVersion && (
                <div className="ml-14 flex items-center gap-3">
                  <span className="text-sm text-gray-600">Number of versions</span>
                  <input
                    type="number"
                    min={2}
                    max={4}
                    value={versionCount}
                    onChange={(e) =>
                      setVersionCount(Math.min(4, Math.max(2, Number(e.target.value))))
                    }
                    className="w-16 rounded-lg border border-gray-300 px-2 py-1.5 text-center text-sm font-semibold focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              )}
            </div>

            {/* Error */}
            {genError && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {genError}
              </p>
            )}

            {/* Generate */}
            <button
              type="button"
              onClick={handleGenerate}
              disabled={!topic || generating}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-500 active:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {generating && <Spinner />}
              {generating ? "Generating…" : "Generate Worksheet"}
            </button>
          </div>
        </Section>

        {/* ══════════════════════════════════════════
            Step 2 — Preview
        ══════════════════════════════════════════ */}

        {/* Loading placeholder */}
        {generating && (
          <div className="flex flex-col items-center gap-3 py-20 text-gray-400">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
            <span className="text-sm">
              {includeSteps
                ? `Generating ${count} problem${count !== 1 ? "s" : ""} with solutions…`
                : `Generating ${count} problem${count !== 1 ? "s" : ""}…`}
            </span>
          </div>
        )}

        {!generating && worksheets.length > 0 && current && (
          <div ref={previewRef} className="space-y-5">
            {/* Header row */}
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900">Preview</h2>
              <span className="text-xs text-gray-400">
                seed&nbsp;
                <code className="font-mono">{current.seed}</code>
                &ensp;·&ensp;
                {current.problems.length}&nbsp;problem
                {current.problems.length !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Version tabs */}
            {worksheets.length > 1 && (
              <div className="flex border-b border-gray-200">
                {worksheets.map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setActiveTab(i)}
                    className={`-mb-px border-b-2 px-5 py-2.5 text-sm font-medium transition-colors ${
                      activeTab === i
                        ? "border-indigo-600 text-indigo-600"
                        : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                    }`}
                  >
                    Version&nbsp;{VERSION_LABELS[i]}
                  </button>
                ))}
              </div>
            )}

            {/* Toggles + steps placement */}
            <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 space-y-4">
              <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
                <Toggle
                  id="answer-key"
                  checked={showAnswerKey}
                  onChange={setShowAnswerKey}
                  label="Include answer key"
                />
                <Toggle
                  id="step-solutions"
                  checked={includeSteps}
                  onChange={handleStepsToggle}
                  label="Step-by-step solutions"
                />
              </div>

              {/* Steps placement — only shown when steps are on */}
              {includeSteps && (
                <div className="ml-14 space-y-2 border-t border-gray-100 pt-3">
                  <span className="text-sm font-medium text-gray-700">
                    PDF placement
                  </span>
                  <div className="flex gap-5">
                    {(
                      [
                        { value: "inline", label: "After each problem" },
                        { value: "separate_page", label: "Separate solutions page" },
                      ] as { value: StepsPlacement; label: string }[]
                    ).map(({ value, label }) => (
                      <label
                        key={value}
                        className="flex cursor-pointer items-center gap-2"
                      >
                        <input
                          type="radio"
                          name="steps-placement"
                          value={value}
                          checked={stepsPlacement === value}
                          onChange={() => setStepsPlacement(value)}
                          className="accent-indigo-600"
                        />
                        <span className="text-sm text-gray-700">{label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Problems */}
            <div className="space-y-3">
              {current.problems.map((p, i) => (
                <ProblemCard
                  key={`${current.version}-${current.seed}-${i}`}
                  index={i}
                  problem={p}
                  showAnswer={showAnswerKey}
                  showSteps={includeSteps}
                />
              ))}
            </div>

            {/* Action bar */}
            <div className="flex gap-3 pb-2 pt-1">
              <button
                type="button"
                onClick={handleDownloadPDF}
                disabled={downloading}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-700 shadow-xs transition-colors hover:bg-gray-50 active:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {downloading ? (
                  <Spinner />
                ) : (
                  <svg
                    className="h-4 w-4 text-gray-500"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 10v6m0 0-3-3m3 3 3-3M3 17V7a2 2 0 0 1 2-2h6l2 2h4a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"
                    />
                  </svg>
                )}
                {downloading ? "Generating PDF…" : "Download PDF"}
              </button>
              <button
                type="button"
                disabled
                title="Available in Phase 3"
                className="flex flex-1 cursor-not-allowed items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white opacity-40"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M17 16v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h2m3-4h6l3 3v7a2 2 0 0 1-2 2h-6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"
                  />
                </svg>
                Save Worksheet
                <span className="text-xs font-normal opacity-60">(Phase 3)</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
