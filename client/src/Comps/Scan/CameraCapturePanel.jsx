import { useEffect, useRef } from "react";

const CameraCapturePanel = ({ stream, onCapture, onCancel }) => {
  const videoRef = useRef(null);

  useEffect(() => {
    if (!videoRef.current || !stream) return;
    videoRef.current.srcObject = stream;
  }, [stream]);

  return (
    <div className="bg-slate-950 text-white rounded-xl p-4 space-y-3">
      <p className="text-xs text-slate-400 text-center">מקמו את הקבלה בתוך המסגרת</p>
      <div className="relative rounded-lg overflow-hidden bg-black border border-slate-700 mx-auto w-full max-w-xs aspect-[3/4]">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover"
          aria-label="camera preview"
        />
        <div className="absolute inset-3 border-2 border-emerald-400 border-dashed rounded-md opacity-60 pointer-events-none" />
      </div>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => onCapture(videoRef.current)}
          className="px-5 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-semibold text-sm"
        >
          צלם עכשיו
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-5 py-2.5 rounded-lg border border-slate-500 text-slate-100 hover:bg-slate-800 font-semibold text-sm"
        >
          ביטול
        </button>
      </div>
    </div>
  );
};

export default CameraCapturePanel;
