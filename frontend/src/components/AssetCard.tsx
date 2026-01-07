import React from 'react';
import { Asset, AssetType, AssetStatus } from '../types';
import { Box, Play, FileText, Download, Clock, AlertTriangle, CheckCircle2, Eye } from 'lucide-react';
import clsx from 'clsx';

const StatusBadge = ({ status }: { status: AssetStatus }) => {
  const styles = {
    [AssetStatus.COMPLETED]: "bg-green-500/10 text-green-400 border-green-500/20",
    [AssetStatus.PROCESSING]: "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse",
    [AssetStatus.PENDING]: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    [AssetStatus.FAILED]: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  const icons = {
    [AssetStatus.COMPLETED]: CheckCircle2,
    [AssetStatus.PROCESSING]: Clock,
    [AssetStatus.PENDING]: Clock,
    [AssetStatus.FAILED]: AlertTriangle,
  };

  const Icon = icons[status];

  return (
    <span className={clsx("flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", styles[status])}>
      <Icon size={12} />
      {status}
    </span>
  );
};

export const AssetCard = ({ asset, onView }: { asset: Asset; onView: () => void }) => {
  const Icon = 
    asset.asset_type === AssetType.MODEL ? Box :
    asset.asset_type === AssetType.VIDEO ? Play : FileText;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-colors group">
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-indigo-500/10 group-hover:text-indigo-400 transition-colors">
          <Icon size={20} />
        </div>
        <StatusBadge status={asset.status} />
      </div>

      <h3 className="font-medium text-slate-200 truncate mb-1" title={asset.filename}>
        {asset.filename}
      </h3>
      <p className="text-xs text-slate-500 mb-4">{asset.asset_type}</p>

      <div className="flex gap-2">
          {/* View Button for Models */}
          {asset.asset_type === AssetType.MODEL && asset.status === AssetStatus.COMPLETED && (
              <button
                onClick={onView}
                className="flex-1 flex items-center justify-center gap-2 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors"
              >
                  <Eye size={14} />
                  View
              </button>
          )}

          {asset.download_url && (
            <a 
              href={asset.download_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className={clsx(
                  "flex items-center justify-center gap-2 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm rounded-lg transition-colors",
                  asset.asset_type === AssetType.MODEL ? "w-auto px-3" : "w-full"
              )}
              title="Download"
            >
              <Download size={14} />
              {asset.asset_type !== AssetType.MODEL && "Download"}
            </a>
          )}
      </div>
      
      {!asset.download_url && asset.status === AssetStatus.COMPLETED && asset.asset_type !== AssetType.MODEL && (
        <div className="text-xs text-center text-slate-500 py-2">
            No Preview Available
        </div>
      )}
    </div>
  );
};
