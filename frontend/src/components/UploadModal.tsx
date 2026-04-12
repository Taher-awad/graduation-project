import { useState, useRef, useEffect } from 'react';
import { Upload, X, File, Check, Loader2, Box, AlertCircle } from 'lucide-react';
import api from '../api/client';
import { AssetType } from '../types';
import type { Asset } from '../types';
import { useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  pendingAsset?: Asset;  // Pre-existing PENDING_SELECTION asset to resume
}

interface ScannedObject {
  name: string;
  type: string;
  vertex_count: number;
}

type Stage = 'pick' | 'scanning' | 'select' | 'done';

export const UploadModal = ({ isOpen, onClose, pendingAsset }: UploadModalProps) => {
  // If a pendingAsset is provided, jump straight to the select stage
  const initialStage: Stage = pendingAsset ? 'select' : 'pick';
  const initialObjects: ScannedObject[] = pendingAsset
    ? ((pendingAsset.metadata_json?.scan_objects ?? []) as ScannedObject[])
    : [];

  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState<AssetType>(AssetType.MODEL);
  const [isSliceable, setIsSliceable] = useState(false);
  const [stage, setStage] = useState<Stage>(initialStage);
  const [pendingAssetId, setPendingAssetId] = useState<string | null>(
    pendingAsset ? pendingAsset.id : null
  );
  const [scannedObjects, setScannedObjects] = useState<ScannedObject[]>(initialObjects);
  const [selectedObjects, setSelectedObjects] = useState<Set<string>>(
    new Set(initialObjects.map((o) => o.name))
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Re-initialise when pendingAsset changes (e.g. user clicks a different card)
  useEffect(() => {
    if (pendingAsset) {
      const objs = (pendingAsset.metadata_json?.scan_objects ?? []) as ScannedObject[];
      setStage('select');
      setPendingAssetId(pendingAsset.id);
      setScannedObjects(objs);
      setSelectedObjects(new Set(objs.map((o) => o.name)));
      setErrorMsg(null);
    } else if (!isOpen) {
      reset();
    }
  }, [pendingAsset, isOpen]);

  const reset = () => {
    setFile(null);
    setStage('pick');
    setPendingAssetId(null);
    setScannedObjects([]);
    setSelectedObjects(new Set());
    setErrorMsg(null);
    if (pollRef.current) clearInterval(pollRef.current);
  };

  useEffect(() => {
    if (!isOpen) reset();
  }, [isOpen]);

  // Poll asset status while scanning
  useEffect(() => {
    if (stage !== 'scanning' || !pendingAssetId) return;

    pollRef.current = setInterval(async () => {
      try {
        const res = await api.get(`/assets/${pendingAssetId}`);
        const asset = res.data;

        if (asset.status === 'PENDING_SELECTION') {
          clearInterval(pollRef.current!);
          const objects: ScannedObject[] = asset.metadata_json?.scan_objects ?? [];
          setScannedObjects(objects);
          // Pre-select all by default
          setSelectedObjects(new Set(objects.map((o: ScannedObject) => o.name)));
          setStage('select');
        } else if (asset.status === 'PROCESSING' || asset.status === 'COMPLETED') {
          // Auto-processed (single object)
          clearInterval(pollRef.current!);
          queryClient.invalidateQueries({ queryKey: ['assets'] });
          setStage('done');
          setTimeout(onClose, 1200);
        } else if (asset.status === 'FAILED') {
          clearInterval(pollRef.current!);
          setErrorMsg(asset.metadata_json?.error ?? 'Scan failed.');
          setStage('pick');
        }
      } catch {
        // keep polling
      }
    }, 1500);

    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [stage, pendingAssetId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setErrorMsg(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setErrorMsg(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('asset_type', type);
    formData.append('is_sliceable', String(isSliceable));

    try {
      const res = await api.post('/assets/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (type === AssetType.MODEL) {
        setPendingAssetId(res.data.id);
        setStage('scanning');
      } else {
        queryClient.invalidateQueries({ queryKey: ['assets'] });
        onClose();
      }
    } catch {
      setErrorMsg('Upload failed. Check connection.');
    }
  };

  const handleConfirmSelection = async () => {
    if (!pendingAssetId || selectedObjects.size === 0) return;
    setErrorMsg(null);

    try {
      await api.post(`/assets/${pendingAssetId}/confirm-selection`, {
        selections: Array.from(selectedObjects),
        is_sliceable: isSliceable,
      });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      setStage('done');
      setTimeout(onClose, 1200);
    } catch {
      setErrorMsg('Failed to confirm selection.');
    }
  };

  const toggleObject = (name: string) => {
    setSelectedObjects(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl p-6 relative"
      >
        <button onClick={() => { reset(); onClose(); }}
          className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors">
          <X size={20} />
        </button>

        <h2 className="text-xl font-bold mb-6">
          {stage === 'pick' && 'Upload New Asset'}
          {stage === 'scanning' && 'Analyzing File…'}
          {stage === 'select' && 'Select Objects to Import'}
          {stage === 'done' && 'Processing Started'}
        </h2>

        {errorMsg && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center gap-2">
            <AlertCircle size={16} className="shrink-0" />
            {errorMsg}
          </div>
        )}

        <AnimatePresence mode="wait">

          {/* ── STAGE 1: FILE PICKER ── */}
          {stage === 'pick' && (
            <motion.div key="pick" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="space-y-6">
              {/* Drop zone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors ${
                  file ? 'border-indigo-500/50 bg-indigo-500/5' : 'border-slate-700 hover:border-slate-500 hover:bg-slate-800/50'
                }`}
              >
                <input
                  type="file"
                  accept={
                    type === AssetType.MODEL ? '.glb,.gltf,.fbx,.obj,.stl,.blend,.zip'
                    : type === AssetType.VIDEO ? '.mp4,.webm'
                    : type === AssetType.IMAGE ? '.png,.jpg,.jpeg,.webp'
                    : '.pdf'
                  }
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
                    <p className="text-sm text-slate-500">GLB, FBX, OBJ, BLEND, ZIP, MP4, PDF, PNG</p>
                  </div>
                )}
              </div>

              {/* Type selector */}
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Asset Type</label>
                <div className="flex gap-2 bg-slate-950 p-1 rounded-lg">
                  {[AssetType.MODEL, AssetType.VIDEO, AssetType.SLIDE, AssetType.IMAGE].map((t) => (
                    <button key={t} onClick={() => setType(t)}
                      className={`flex-1 py-1.5 text-sm rounded-md transition-colors ${
                        type === t ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                      }`}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Sliceable toggle */}
              {type === AssetType.MODEL && (
                <div className="flex items-center gap-3 p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <div
                    onClick={() => setIsSliceable(!isSliceable)}
                    className={`w-5 h-5 rounded border flex items-center justify-center cursor-pointer shrink-0 ${
                      isSliceable ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-slate-600'
                    }`}
                  >
                    {isSliceable && <Check size={14} />}
                  </div>
                  <span className="text-sm text-slate-300">Enable Physics Slicing (VR)</span>
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={!file}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Upload & Analyze
              </button>
            </motion.div>
          )}

          {/* ── STAGE 2: SCANNING ── */}
          {stage === 'scanning' && (
            <motion.div key="scanning" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="py-10 flex flex-col items-center gap-5">
              <div className="relative w-20 h-20">
                <div className="absolute inset-0 rounded-full border-4 border-indigo-500/20" />
                <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-indigo-500 animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Loader2 size={28} className="text-indigo-400 animate-spin" />
                </div>
              </div>
              <div className="text-center">
                <p className="font-semibold text-slate-200">Analyzing file contents…</p>
                <p className="text-sm text-slate-500 mt-1">
                  Detecting objects and removing environment props
                </p>
              </div>
            </motion.div>
          )}

          {/* ── STAGE 3: OBJECT SELECTOR ── */}
          {stage === 'select' && (
            <motion.div key="select" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="space-y-4">
              <p className="text-sm text-slate-400">
                {scannedObjects.length} object{scannedObjects.length !== 1 ? 's' : ''} found.
                Select which to import — each becomes its own asset.
              </p>

              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {scannedObjects.map((obj) => {
                  const selected = selectedObjects.has(obj.name);
                  return (
                    <div
                      key={obj.name}
                      onClick={() => toggleObject(obj.name)}
                      className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                        selected
                          ? 'border-indigo-500/60 bg-indigo-500/8'
                          : 'border-slate-700 hover:border-slate-600 bg-slate-950'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 ${
                        selected ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-slate-600'
                      }`}>
                        {selected && <Check size={13} />}
                      </div>
                      <div className="w-8 h-8 bg-slate-800 rounded-lg flex items-center justify-center shrink-0">
                        <Box size={16} className="text-indigo-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-200 truncate">{obj.name}</p>
                        <p className="text-xs text-slate-500">
                          {obj.type} · {obj.vertex_count.toLocaleString()} verts
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Sliceable toggle for selected objects */}
              <div className="flex items-center gap-3 p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div
                  onClick={() => setIsSliceable(!isSliceable)}
                  className={`w-5 h-5 rounded border flex items-center justify-center cursor-pointer shrink-0 ${
                    isSliceable ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-slate-600'
                  }`}
                >
                  {isSliceable && <Check size={14} />}
                </div>
                <span className="text-sm text-slate-300">Enable Physics Slicing (VR)</span>
              </div>

              <button
                onClick={handleConfirmSelection}
                disabled={selectedObjects.size === 0}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Import Selected ({selectedObjects.size})
              </button>
            </motion.div>
          )}

          {/* ── STAGE 4: DONE ── */}
          {stage === 'done' && (
            <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="py-10 flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-emerald-500/15 flex items-center justify-center">
                <Check size={32} className="text-emerald-400" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-slate-200">Processing started!</p>
                <p className="text-sm text-slate-500 mt-1">Your asset(s) will appear once ready.</p>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </motion.div>
    </div>
  );
};
