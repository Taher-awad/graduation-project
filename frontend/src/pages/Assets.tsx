import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import { Asset } from '../types';
import { AssetCard } from '../components/AssetCard';
import { UploadModal } from '../components/UploadModal';
import { ViewerModal } from '../components/ViewerModal';
import { Plus, Search } from 'lucide-react';

export const Assets = () => {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const { data: assets, isLoading, error } = useQuery<Asset[]>({
    queryKey: ['assets'],
    queryFn: async () => {
      const response = await api.get('/assets/');
      return response.data;
    }
  });

  const filteredAssets = assets?.filter(a => 
    a.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div>
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center mb-8">
        {/* Search */}
        <div className="relative flex-1 max-w-md w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input 
                type="text" 
                placeholder="Search assets..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
            />
        </div>

        {/* Action */}
        <button 
            onClick={() => setIsUploadOpen(true)}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
            <Plus size={18} />
            Upload Asset
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-slate-500">Loading assets...</div>
      ) : error ? (
        <div className="text-center py-20 text-red-400">Failed to load assets</div>
      ) : filteredAssets?.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-slate-800 rounded-xl">
            <p className="text-slate-400 mb-2">No assets found</p>
            <p className="text-sm text-slate-600">Upload your first model, video, or slide.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredAssets?.map((asset) => (
                <AssetCard 
                    key={asset.id} 
                    asset={asset} 
                    onView={() => setSelectedAsset(asset)}
                />
            ))}
        </div>
      )}

      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />
      <ViewerModal asset={selectedAsset} onClose={() => setSelectedAsset(null)} />
    </div>
  );
};
