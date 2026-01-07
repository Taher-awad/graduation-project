import { X, ExternalLink } from 'lucide-react';
import { ModelViewer } from './ModelViewer';
import type { Asset } from '../types';

interface ViewerModalProps {
  asset: Asset | null;
  onClose: () => void;
}

export const ViewerModal = ({ asset, onClose }: ViewerModalProps) => {
  if (!asset) return null;

  // Use processed path if available (via Presigned URL typically), else try raw?
  // Our API returns 'download_url'.
  // Note: MinIO localhost URL needs to be accessible by browser.
  // If running inside Docker, 'minio:9000' won't work for host browser.
  // We need to ensure the download_url is localhost:9000.
  // The backend generates it based on MINIO_ENDPOINT which is often 'minio' in docker-compose.
  // For this demo, let's blindly replace minio with localhost if needed or trust the backend.
  
  const modelUrl = asset.download_url?.replace("http://minio:9000", "http://localhost:9000");

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[80vh] flex flex-col shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-slate-200">{asset.filename}</h2>
            <p className="text-xs text-slate-500 uppercase tracking-wider">{asset.asset_type}</p>
          </div>
          <div className="flex items-center gap-2">
             {asset.download_url && (
                <a 
                    href={asset.download_url} 
                    target="_blank"
                    rel="noreferrer"
                    className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
                    title="Download Original"
                >
                    <ExternalLink size={20} />
                </a>
             )}
            <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors">
                <X size={20} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 bg-black/20 p-4 relative">
            {modelUrl ? (
                <ModelViewer url={modelUrl} />
            ) : (
                <div className="flex items-center justify-center h-full text-slate-500">
                    Preview not available (Asset Processing or URL expired)
                </div>
            )}
        </div>
      </div>
    </div>
  );
};
