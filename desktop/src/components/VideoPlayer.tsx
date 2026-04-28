import { useEffect, useRef } from "react";

interface Props {
  src: string;
  seekTo?: number; // seconds
}

export function VideoPlayer({ src, seekTo }: Props) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (ref.current && seekTo != null) {
      ref.current.currentTime = seekTo;
      ref.current.play().catch(() => {});
    }
  }, [seekTo]);

  return (
    <div className="video-card">
      <video ref={ref} src={src} controls preload="metadata" style={{ width: "100%", display: "block" }}>
        Video not available.
      </video>
    </div>
  );
}
