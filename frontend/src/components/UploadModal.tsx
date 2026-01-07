import { useState, useRef } from 'react';
import { Upload, X, File, Check } from 'lucide-react';
import api from '../api/client';
import { AssetType } from '../types';
import { useQueryClient } from '@tanstack/react-query';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const UploadModal = ({ isOpen, onClose }: UploadModalProps) => {
  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState<AssetType>(AssetType.MODEL);
  const [isSliceable, setIsSliceable] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("asset_type", type);
    formData.append("is_sliceable", String(isSliceable));

    try {
      await api.post('/assets/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      onClose();
      setFile(null);
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl p-6 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-slate-500 hover:text-white">
          <X size={20} />
        </button>

        <h2 className="text-xl font-bold mb-6">Upload New Asset</h2>

        <div className="space-y-6">
          {/* File Drop Area */}
          <div 
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors ${
              file ? "border-indigo-500/50 bg-indigo-500/5" : "border-slate-700 hover:border-slate-500 hover:bg-slate-800/50"
            }`}
          >
            <input 
              type="file" 
              ref={fileInputRef}
              className="hidden" 
              onChange={handleFileChange}
            />
            
            {file ? (
              <div className="text-center">
                <div className="w-12 h-12 bg-indigo-500/10 text-indigo-400 rounded-full flex items-center justify-center mx-auto mb-3">
                  <File size={24} />
                </div>
                <p className="font-medium text-slate-200">{file.name}</p>
                <p className="text-sm text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="text-center">
                <div className="w-12 h-12 bg-slate-800 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Upload size={24} />
                </div>
                <p className="font-medium text-slate-200">Click to browse</p>
                <p className="text-sm text-slate-500">Supports GLB, FBX, OBJ, BLEND, MP4, PDF</p>
              </div>
            )}
          </div>

          {/* Type Selection */}
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">Asset Type</label>
            <div className="flex gap-2 bg-slate-950 p-1 rounded-lg">
                {[AssetType.MODEL, AssetType.VIDEO, AssetType.SLIDE].map((t) => (
                    <button
                        key={t}
                        onClick={() => setType(t)}
                        className={`flex-1 py-1.5 text-sm rounded-md transition-colors ${
                            type === t ? "bg-indigo-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
                        }`}
                    >
                        {t}
                    </button>
                ))}
            </div>
          </div>

          {/* Slicing Option (Only for Models) */}
          {type === AssetType.MODEL && (
            <div className="flex items-center gap-3 p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div 
                    onClick={() => setIsSliceable(!isSliceable)}
                    className={`w-5 h-5 rounded border flex items-center justify-center cursor-pointer ${
                        isSliceable ? "bg-indigo-500 border-indigo-500 text-white" : "border-slate-600"
                    }`}
                >
                    {isSliceable && <Check size={14} />}
                </div>
                <span className="text-sm text-slate-300">Enable Physics Slicing (VR)</span>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? 'Uploading...' : 'Start Upload'}
          </button>
        </div>
      </div>
    </div>
  );
};
