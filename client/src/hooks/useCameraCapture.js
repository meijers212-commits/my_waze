import { useCallback, useEffect, useState } from "react";

const createReceiptFileFromVideo = async (videoElement) => {
  if (!videoElement?.videoWidth || !videoElement?.videoHeight) {
    throw new Error("camera_not_ready");
  }

  const canvas = document.createElement("canvas");
  canvas.width = videoElement.videoWidth;
  canvas.height = videoElement.videoHeight;
  const context = canvas.getContext("2d");

  if (!context) {
    throw new Error("canvas_unavailable");
  }

  context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

  const blob = await new Promise((resolve) => {
    canvas.toBlob(resolve, "image/jpeg", 0.9);
  });

  if (!blob) {
    throw new Error("capture_failed");
  }

  return new File([blob], `receipt-${Date.now()}.jpg`, { type: "image/jpeg" });
};

export const useCameraCapture = () => {
  const [stream, setStream] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const stopCamera = useCallback(() => {
    setStream((currentStream) => {
      currentStream?.getTracks().forEach((track) => track.stop());
      return null;
    });
  }, []);

  const closeCamera = useCallback(() => {
    stopCamera();
    setIsOpen(false);
  }, [stopCamera]);

  const openCamera = useCallback(async () => {
    if (!navigator?.mediaDevices?.getUserMedia) {
      setError("המצלמה לא נתמכת בדפדפן הזה.");
      return;
    }

    stopCamera();
    setLoading(true);
    setError("");

    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          aspectRatio: { ideal: 3 / 4 },
          width: { ideal: 1080 },
          height: { ideal: 1440 },
        },
        audio: false,
      });
      setStream(nextStream);
      setIsOpen(true);
    } catch {
      setError("לא הצלחנו לפתוח את המצלמה. בדוק הרשאות מצלמה.");
      setIsOpen(false);
    } finally {
      setLoading(false);
    }
  }, [stopCamera]);

  const capturePhoto = useCallback(async (videoElement) => {
    const file = await createReceiptFileFromVideo(videoElement);
    closeCamera();
    return file;
  }, [closeCamera]);

  useEffect(() => stopCamera, [stopCamera]);

  return {
    stream,
    isOpen,
    error,
    loading,
    openCamera,
    closeCamera,
    capturePhoto,
  };
};
