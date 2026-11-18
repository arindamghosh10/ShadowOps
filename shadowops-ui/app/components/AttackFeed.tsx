// =============================================================================
// components/AttackFeed.tsx — Live Scrolling Attack Log
//
// Shows each adversarial input as it is sent to the target agent.
// Green dot = agent passed (secure). Red dot = agent was exploited.
// =============================================================================

export interface AttackEntry {
  id: number;
  input: string;
  passed: boolean;
  timestamp: string;
}

interface AttackFeedProps {
  entries: AttackEntry[];
  isRunning: boolean;
}

export default function AttackFeed({ entries, isRunning }: AttackFeedProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Terminal header bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-800 bg-gray-900">
        <span className="w-3 h-3 rounded-full bg-red-500 opacity-70" />
        <span className="w-3 h-3 rounded-full bg-yellow-500 opacity-70" />
        <span className="w-3 h-3 rounded-full bg-green-500 opacity-70" />
        <span className="ml-2 text-xs text-gray-500 font-mono">
          attack_feed — {entries.length} attempts
        </span>
        {isRunning && (
          <span className="ml-auto flex items-center gap-1.5 text-xs text-indigo-400">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            Live
          </span>
        )}
      </div>

      {/* Feed entries */}
      <div className="h-80 overflow-y-auto font-mono text-xs p-3 space-y-2">
        {entries.length === 0 && (
          <p className="text-gray-600 text-center pt-8">
            {isRunning ? "Waiting for first attack..." : "Start a test run to see attacks"}
          </p>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className="flex gap-2 items-start">
            <span className="text-gray-600 shrink-0 pt-0.5">{entry.timestamp}</span>
            <span
              className={`w-2 h-2 rounded-full shrink-0 mt-1 ${
                entry.passed ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className={entry.passed ? "text-gray-300" : "text-red-300"}>
              {entry.input}
            </span>
          </div>
        ))}
        {isRunning && (
          <div className="flex gap-2 items-center text-gray-600">
            <span className="animate-pulse">▌</span>
            <span>Generating next attack...</span>
          </div>
        )}
      </div>
    </div>
  );
}
