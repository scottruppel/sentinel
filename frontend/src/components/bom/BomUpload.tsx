import { useState, useCallback } from 'react';
import { api } from '../../api/client';

interface BomUploadProps {
  onUploaded: () => void;
  onClose: () => void;
}

export default function BomUpload({ onUploaded, onClose }: BomUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [program, setProgram] = useState('');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      setFile(dropped);
      if (!name) setName(dropped.name.replace(/\.[^.]+$/, ''));
    }
  }, [name]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !name.trim()) return;

    setUploading(true);
    setError(null);
    try {
      await api.boms.upload(file, name, program || undefined, description || undefined);
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">Upload BOM</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragOver ? 'border-sentinel-500 bg-sentinel-50' : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            {file ? (
              <p className="text-sm text-gray-700">{file.name} ({(file.size / 1024).toFixed(1)} KB)</p>
            ) : (
              <>
                <p className="text-gray-500">Drag & drop a BOM file here</p>
                <p className="text-xs text-gray-400 mt-1">.xlsx or .csv</p>
              </>
            )}
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) { setFile(f); if (!name) setName(f.name.replace(/\.[^.]+$/, '')); }
              }}
              className="hidden"
              id="bom-file"
            />
            <label htmlFor="bom-file" className="mt-3 inline-block px-3 py-1 text-sm text-sentinel-600 border border-sentinel-300 rounded cursor-pointer hover:bg-sentinel-50">
              Browse files
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">BOM Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-sentinel-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Program</label>
            <input
              type="text"
              value={program}
              onChange={(e) => setProgram(e.target.value)}
              placeholder="e.g., weapon system or project name"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-sentinel-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-sentinel-500"
            />
          </div>

          {error && <p className="text-sm text-risk-critical">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50">Cancel</button>
            <button type="submit" disabled={!file || !name.trim() || uploading} className="px-4 py-2 text-sm text-white bg-sentinel-600 rounded-md hover:bg-sentinel-700 disabled:opacity-50">
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
