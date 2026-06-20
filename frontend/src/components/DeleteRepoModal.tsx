import { useState } from "react";
import { Loader2, AlertTriangle, Trash2 } from "lucide-react";
import { ConnectedRepo } from "../services/repoService";

interface DeleteRepoModalProps {
  repo: ConnectedRepo | null;
  open: boolean;
  onClose: () => void;
  onConfirm: (repoId: string) => Promise<void>;
}

export default function DeleteRepoModal({ repo, open, onClose, onConfirm }: DeleteRepoModalProps) {
  const [confirmName, setConfirmName] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  if (!open || !repo) return null;

  const handleConfirm = async () => {
    if (confirmName !== repo.name) return;
    setIsDeleting(true);
    try {
      await onConfirm(repo.id);
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-red-900/50 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="p-6">
          <div className="flex items-center gap-3 text-red-500 mb-4">
            <div className="p-2 bg-red-500/10 rounded-lg">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">Delete Repository</h2>
          </div>
          
          <div className="text-gray-300 space-y-4 mb-6 text-sm leading-relaxed">
            <p>
              This action <span className="font-bold text-white">cannot be undone</span>.
            </p>
            <p>
              This will permanently remove <span className="font-bold text-white">{repo.full_name}</span> along with all:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-gray-400">
              <li>Analysis data and graph nodes</li>
              <li>Architecture intelligence</li>
              <li>Workflows and impact reports</li>
              <li>Repository history</li>
            </ul>
            <p>
              Please type <span className="font-mono bg-gray-800 px-1.5 py-0.5 rounded text-red-400">{repo.name}</span> to confirm.
            </p>
          </div>

          <input
            type="text"
            value={confirmName}
            onChange={(e) => setConfirmName(e.target.value)}
            className="w-full px-4 py-2.5 bg-gray-950 border border-gray-800 rounded-lg focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all font-mono"
            placeholder={repo.name}
            disabled={isDeleting}
          />
        </div>

        <div className="p-4 bg-gray-950 border-t border-gray-800 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={confirmName !== repo.name || isDeleting}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-500 disabled:opacity-50 disabled:hover:bg-red-600 rounded-lg transition-colors text-white"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                Delete Repository
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
