import { X, ExternalLink } from 'lucide-react';
import { ModelViewer } from './ModelViewer';
import type { Asset } from '../types';
import { AssetType } from '../types';

const VideoViewer = ({ url }: { url: string }) => (
  <video src={url} controls className="max-w-full max-h-[80vh] rounded-lg shadow-2xl" autoPlay />
);

const ImageViewer = ({ url }: { url: string }) => (
  <img src={url} alt="Asset" className="max-w-full max-h-[80vh] object-contain rounded-lg shadow-2xl" />
);

const PdfViewer = ({ url }: { url: string }) => (
  <iframe src={url} className="w-full h-[80vh] bg-white rounded-lg shadow-2xl" title="PDF Viewer" />
);

const GenericViewer = ({ url, filename }: { url: string; filename: string }) => (
  <div className="flex flex-col items-center justify-center p-8 bg-white dark:bg-slate-900 rounded-xl max-w-md text-center">
    <p className="text-lg font-semibold mb-4 text-slate-900 dark:text-white">Cannot preview {filename}</p>
    <a 
      href={url} 
      target="_blank" 
      rel="noopener noreferrer"
      className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition-colors"
    >
      <ExternalLink size={20} />
      Download / Open Externally
    </a>
  </div>
);

export const ViewerModal = ({ asset, onClose }: { asset: Asset | null; onClose: () => void }) => {
  if (!asset) return null;

  // Code previously replaced 'minio' with 'localhost', but this broke the 'minioadmin' credential key.
  // Backend now generates correct localhost URLs using s3_signer.
  const modelUrl = asset.download_url;

  const renderContent = () => {
    if (!modelUrl) {
      return (
        <div className="p-8 bg-white dark:bg-slate-900 rounded-xl">
           <p className="text-slate-500">Preview not available (Asset Processing or URL expired)</p>
        </div>
      );
    }

    switch (asset.asset_type) {
      case AssetType.MODEL:
        return <div className="w-[90vw] h-[80vh] max-w-6xl"><ModelViewer url={modelUrl} /></div>;
      case AssetType.VIDEO:
        return <VideoViewer url={modelUrl} />;
      case AssetType.IMAGE:
        return <ImageViewer url={modelUrl} />;
      case AssetType.SLIDE:
        // Simple check for PDF vs generic file
        if (asset.filename.toLowerCase().endsWith('.pdf')) {
            return <div className="w-[90vw] max-w-6xl"><PdfViewer url={modelUrl} /></div>;
        }
        return <GenericViewer url={modelUrl} filename={asset.filename} />;
      default:
        return <GenericViewer url={modelUrl} filename={asset.filename} />;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <button 
        onClick={onClose}
        className="absolute top-4 right-4 text-white/50 hover:text-white p-2 transition-colors z-[60]"
      >
        <X size={32} />
      </button>
      
      {renderContent()}
    </div>
  );
};
