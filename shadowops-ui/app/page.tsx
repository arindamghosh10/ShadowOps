"use client";

// =============================================================================
// app/page.tsx — ShadowOps Dashboard Home
//
// LEARNING NOTE — Next.js 14 App Router
//
// In Next.js 14, every file in /app is a Server Component by default.
// Adding "use client" at the top makes it a Client Component, which means:
//   - It runs in the browser, not on the server
//   - It can use React hooks (useState, useEffect)
//   - It can interact with the DOM and make API calls from the browser
//
// We need "use client" here because we poll the API and update state
// based on the poll results — that requires useState and useEffect.
// =============================================================================

import { useState, useEffect, useRef } from "react";
import AttackFeed, { AttackEntry } from "./components/AttackFeed";
import VulnerabilityCard from "./components/VulnerabilityCard";
import PatchDiffViewer from "./components/PatchDiffViewer";

const API_BASE = "http://localhost:8000";

interface RunResults {
  run_id: string;
  status: string;
  target_name: string;
  attacks_launched: number;
  vulnerabilities_found: Vulnerability[];
  proposed_patch: string | null;
  resiliency_score: number | null;
}

interface Vulnerability {
  bug_type: string;
  severity: string;
  root_cause: string;
  affected_function: string;
}

export default function Dashboard() {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [results, setResults] = useState<RunResults | null>(null);
  const [attackFeed, setAttackFeed] = useState<AttackEntry[]>([]);
  const [selectedPatch, setSelectedPatch] = useState<string | null>(null);
  const [attackCount, setAttackCount] = useState(0);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Start a new test run
  const startRun = async () => {
    setStatus("starting");
    setResults(null);
    setAttackFeed([]);
    setAttackCount(0);

    const res = await fetch(`${API_BASE}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_name: "Refund Bot v1" }),
    });
    const data = await res.json();
    setRunId(data.run_id);
  };

  // Poll for status updates
  useEffect(() => {
    if (!runId) return;

    const poll = async () => {
      try {
        const statusRes = await fetch(`${API_BASE}/status/${runId}`);
        const statusData = await statusRes.json();

        setStatus(statusData.status);
        setAttackCount(statusData.attacks_launched);

        // Simulate attack feed entries as attacks come in
        if (statusData.attacks_launched > attackFeed.length) {
          setAttackFeed((prev) => [
            ...prev,
            {
              id: Date.now(),
              input: `Attack #${statusData.attacks_launched} sent to target agent...`,
              passed: statusData.vulnerabilities_found === 0,
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
        }

        if (statusData.status !== "running" && statusData.status !== "starting") {
          clearInterval(pollRef.current!);
          // Fetch full results
          const resultsRes = await fetch(`${API_BASE}/results/${runId}`);
          if (resultsRes.ok) {
            const fullResults = await resultsRes.json();
            setResults(fullResults);
          }
        }
      } catch {
        // API not ready yet — keep polling
      }
    };

    pollRef.current = setInterval(poll, 2000);
    return () => clearInterval(pollRef.current!);
  }, [runId]);

  const isRunning = status === "running" || status === "starting";
  const resiliencyColor =
    (results?.resiliency_score ?? 100) >= 80
      ? "text-green-400"
      : (results?.resiliency_score ?? 100) >= 50
      ? "text-yellow-400"
      : "text-red-400";

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">ShadowOps</h1>
            <p className="text-gray-400 text-sm mt-1">
              E-Commerce AI Agent Stress Tester
            </p>
          </div>
          <button
            onClick={startRun}
            disabled={isRunning}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700
                       disabled:text-gray-500 rounded-lg text-sm font-medium transition-colors"
          >
            {isRunning ? "Running..." : "Start Test"}
          </button>
        </div>

        {/* Resiliency score bar — shows when results are available */}
        {results && (
          <div className="grid grid-cols-4 gap-4 mb-8">
            {[
              { label: "Resiliency score", value: `${results.resiliency_score}%`, color: resiliencyColor },
              { label: "Attacks launched", value: results.attacks_launched },
              { label: "Vulnerabilities", value: results.vulnerabilities_found.length },
              { label: "Status", value: results.status.replace("_", " ") },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <p className="text-xs text-gray-400 mb-1">{label}</p>
                <p className={`text-2xl font-semibold ${color || "text-white"}`}>{value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Two-column layout: attack feed + vulnerability cards */}
        <div className="grid grid-cols-2 gap-6">
          {/* Left: live attack feed */}
          <div>
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
              Live attack feed
            </h2>
            <AttackFeed entries={attackFeed} isRunning={isRunning} />
          </div>

          {/* Right: vulnerability cards */}
          <div>
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
              Vulnerabilities found
            </h2>
            {results?.vulnerabilities_found.length ? (
              results.vulnerabilities_found.map((v, i) => (
                <VulnerabilityCard
                  key={i}
                  vulnerability={v}
                  onViewPatch={() => setSelectedPatch(results.proposed_patch)}
                />
              ))
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center text-gray-500 text-sm">
                {isRunning ? "Scanning for vulnerabilities..." : "No test run yet"}
              </div>
            )}
          </div>
        </div>

        {/* Patch diff viewer — shown when user clicks "View Patch" */}
        {selectedPatch && (
          <div className="mt-6">
            <PatchDiffViewer
              patch={selectedPatch}
              onClose={() => setSelectedPatch(null)}
            />
          </div>
        )}
      </div>
    </main>
  );
}
