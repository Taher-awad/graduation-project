import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import type { Asset } from '../types';
import { AssetStatus } from '../types';
import { AssetCard } from '../components/AssetCard';
import { UploadModal } from '../components/UploadModal';
import { ViewerModal } from '../components/ViewerModal';
import { Plus, Search, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

export const Assets = () => {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [pendingAsset, setPendingAsset] = useState<Asset | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const { data: assets, isLoading, error, refetch } = useQuery<Asset[]>({
    queryKey: ['assets'],
    queryFn: async () => {
      const response = await api.get('/assets/');
      return response.data;
    },
    refetchInterval: 5000
  });

  const filteredAssets = assets?.filter(a =>
    a.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleContinueSelection = (asset: Asset) => {
    setPendingAsset(asset);
    setIsUploadOpen(true);
  };

  const handleUploadClose = () => {
    setIsUploadOpen(false);
    setPendingAsset(null);
    refetch();
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center mb-8">
        <div className="relative flex-1 max-w-md w-full group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 transition-colors" size={20} />
          <input
            type="text"
            placeholder="Search assets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-10 pr-4 py-3 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 shadow-sm transition-all"
          />
        </div>

        <button
          onClick={() => { setPendingAsset(null); setIsUploadOpen(true); }}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-3 rounded-xl font-semibold shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 transition-all active:scale-95"
        >
          <Plus size={20} />
          Upload Asset
        </button>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-32 text-slate-400">
          <Loader2 className="animate-spin mb-4 text-indigo-500" size={40} />
          <p className="font-medium">Loading assets...</p>
        </div>
      ) : error ? (
        <div className="text-center py-20 bg-red-50 dark:bg-red-900/10 rounded-2xl border border-red-100 dark:border-red-900/30">
          <p className="text-red-500 font-medium">Failed to load assets</p>
        </div>
      ) : filteredAssets?.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl bg-slate-50/50 dark:bg-slate-900/50 flex flex-col items-center justify-center">
          <motion.img
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            src="/assets/empty-state.png"
            alt="No Assets"
            className="w-64 h-64 object-contain mb-6 opacity-90 drop-shadow-2xl"
          />
          <p className="text-slate-900 dark:text-white font-bold text-xl mb-2">Your asset library is empty</p>
          <p className="text-slate-500 dark:text-slate-400 max-w-sm mx-auto mb-8">
            Upload 3D models, videos, or slides to get started building your virtual classroom.
          </p>
          <button
            onClick={() => { setPendingAsset(null); setIsUploadOpen(true); }}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-semibold shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 transition-all active:scale-95"
          >
            <Plus size={20} />
            Upload First Asset
          </button>
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
        >
          {filteredAssets?.map((asset) => (
            <AssetCard
              key={asset.id}
              asset={asset}
              onView={() => setSelectedAsset(asset)}
              onDelete={() => refetch()}
              onContinueSelection={
                asset.status === AssetStatus.PENDING_SELECTION
                  ? () => handleContinueSelection(asset)
                  : undefined
              }
            />
          ))}
        </motion.div>
      )}

      <UploadModal
        isOpen={isUploadOpen}
        onClose={handleUploadClose}
        pendingAsset={pendingAsset ?? undefined}
      />
      <ViewerModal asset={selectedAsset} onClose={() => setSelectedAsset(null)} />
    </div>
  );
};
