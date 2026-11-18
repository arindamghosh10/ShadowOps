// =============================================================================
// components/PatchDiffViewer.tsx — Before/After Code Diff
//
// Shows the proposed patch with ORIGINAL and PATCHED sections highlighted.
// The Approve and Reject buttons call back to the API in Phase 3.
// =============================================================================

interface PatchDiffViewerProps {
  patch: string;
  onClose: () => void;
  onApprove?: () => void;
  onReject?: () => void;
}

export default function PatchDiffViewer({
  patch,
  onClose,
  onApprove,
  onReject,
}: PatchDiffViewerProps) {
  const lines = patch.split("\n");

  const getLineStyle = (line: string) => {
    if (line.startsWith("+") && !line.startsWith("+++"))
      return "bg-green-950 text-green-300";
    if (line.startsWith("-") && !line.startsWith("---"))
      return "bg-red-950 text-red-300";
    if (line.startsWith("ORIGINAL") || line.startsWith("PATCHED") || line.startsWith("REASON"))
      return "text-gray-400 font-semibold";
    if (line.startsWith("---") || line.startsWith("==="))
      return "text-gray-700";
    return "text-gray-300";
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h3 className="text-sm font-medium text-gray-200">Proposed patch</h3>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-lg leading-none">
          ×
        </button>
      </div>

      {/* Diff body */}
      <div className="font-mono text-xs overflow-x-auto max-h-96 overflow-y-auto p-4 space-y-0.5">
        {lines.map((line, i) => (
          <div key={i} className={`px-2 py-0.5 rounded ${getLineStyle(line)}`}>
            {line || "\u00A0"}
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 px-4 py-3 border-t border-gray-800">
        <button
          onClick={onApprove}
          className="px-4 py-2 bg-green-800 hover:bg-green-700 text-green-100
                     rounded-lg text-sm font-medium transition-colors"
        >
          Approve patch
        </button>
        <button
          onClick={onReject}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300
                     rounded-lg text-sm font-medium transition-colors"
        >
          Reject
        </button>
        <button
          onClick={onClose}
          className="ml-auto text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
}
