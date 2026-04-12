import { AssetType, AssetStatus } from '../types';
import type { Asset } from '../types';
import { Box, Play, FileText, Download, Clock, AlertTriangle, CheckCircle2, Eye, Trash2, Search } from 'lucide-react';
import clsx from 'clsx';
import { motion } from 'framer-motion';
import api from '../api/client';

const StatusBadge = ({ status }: { status: AssetStatus }) => {
  const styles: Record<string, string> = {
    [AssetStatus.COMPLETED]: "bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20",
    [AssetStatus.PROCESSING]: "bg-blue-50 text-blue-600 border-blue-100 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20 animate-pulse",
    [AssetStatus.SCANNING]: "bg-blue-50 text-blue-600 border-blue-100 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20 animate-pulse",
    [AssetStatus.PENDING_SELECTION]: "bg-indigo-50 text-indigo-600 border-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-400 dark:border-indigo-500/20",
    [AssetStatus.PENDING]: "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-500/10 dark:text-slate-400 dark:border-slate-500/20",
    [AssetStatus.FAILED]: "bg-red-50 text-red-600 border-red-100 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20",
  };

  const icons: Record<string, React.ElementType> = {
    [AssetStatus.COMPLETED]: CheckCircle2,
    [AssetStatus.PROCESSING]: Clock,
    [AssetStatus.SCANNING]: Clock,
    [AssetStatus.PENDING_SELECTION]: Search,
    [AssetStatus.PENDING]: Clock,
    [AssetStatus.FAILED]: AlertTriangle,
  };

  const Icon = icons[status] ?? Clock;

  return (
    <span className={clsx("flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border", styles[status] ?? styles[AssetStatus.PENDING])}>
      <Icon size={12} strokeWidth={3} />
      {status.replace('_', ' ')}
    </span>
  );
};

interface AssetCardProps {
  asset: Asset;
  onView: () => void;
  onDelete?: () => void;
  onContinueSelection?: () => void;
}

export const AssetCard = ({ asset, onView, onDelete, onContinueSelection }: AssetCardProps) => {
  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this asset?')) return;
    try {
      if (onDelete) {
         await api.delete(`/assets/${asset.id}`);
         onDelete();
      }
    } catch {
      alert('Failed to delete asset');
    }
  };

  const Icon = 
    asset.asset_type === AssetType.MODEL ? Box :
    asset.asset_type === AssetType.VIDEO ? Play : 
    asset.asset_type === AssetType.IMAGE ? Eye : FileText;

  return (
    <motion.div 
        layout
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        whileHover={{ y: -4 }}
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-xl hover:shadow-indigo-500/10 dark:hover:shadow-indigo-900/10 transition-all duration-300 group flex flex-col justify-between h-full"
    >
      <div>
        <div className="flex items-start justify-between mb-5">
            <div className="w-12 h-12 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 flex items-center justify-center text-slate-500 dark:text-slate-400 group-hover:bg-indigo-50 dark:group-hover:bg-indigo-500/20 group-hover:text-indigo-600 dark:group-hover:text-indigo-300 group-hover:border-indigo-100 dark:group-hover:border-indigo-500/30 transition-colors duration-300 overflow-hidden relative">
                {asset.asset_type === AssetType.IMAGE && asset.download_url ? (
                  <img src={asset.download_url} alt="" className="w-full h-full object-cover" />
                ) : (
                  <Icon size={24} />
                )}
            </div>
            <StatusBadge status={asset.status} />
        </div>

        <h3 className="font-semibold text-slate-900 dark:text-slate-100 truncate mb-1 text-lg" title={asset.filename}>
            {asset.filename}
        </h3>
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-6">{asset.asset_type}</p>
      </div>

      <div className="flex gap-2.5 mt-auto">
          {/* Continue Selection button for PENDING_SELECTION */}
          {asset.status === AssetStatus.PENDING_SELECTION && onContinueSelection && (
              <button
                onClick={onContinueSelection}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-indigo-500/20"
              >
                <Search size={16} />
                Select Objects
              </button>
          )}

          {/* View Button for completed */}
          {asset.status === AssetStatus.COMPLETED && (
              <button
                onClick={onView}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30"
              >
                  <Eye size={16} />
                  View
              </button>
          )}

          {asset.download_url && (
            <a 
              href={asset.download_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className={clsx(
                  "flex items-center justify-center gap-2 py-2.5 border text-sm font-medium rounded-xl transition-colors w-12",
                  "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 hover:border-slate-300"
              )}
              title="Download"
            >
              <Download size={16} />
            </a>
          )}
          
          <button
              onClick={handleDelete}
              className="flex items-center justify-center gap-2 py-2.5 px-3 border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-500/10 text-red-600 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-xl transition-colors"
              title="Delete"
          >
              <Trash2 size={16} />
          </button>
      </div>
      
      {!asset.download_url && asset.status === AssetStatus.COMPLETED && asset.asset_type !== AssetType.MODEL && (
        <div className="text-xs text-center text-slate-400 py-2.5 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
            No Preview
        </div>
      )}
    </motion.div>
  );
};
