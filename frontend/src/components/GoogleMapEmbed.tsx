'use client';

/**
 * GoogleMapEmbed – renders a Google Maps Embed API iframe.
 * Uses NEXT_PUBLIC_GOOGLE_MAPS_EMBED_API_KEY from environment.
 * Does NOT expose the key in user-visible HTML attributes beyond the src URL
 * (same security level as any public embed key).
 */

interface GoogleMapEmbedProps {
  /** Free-form address / place name */
  q: string;
  /** Zoom level 1-21 (default 12) */
  zoom?: number;
  className?: string;
  height?: number | string;
}

export default function GoogleMapEmbed({
  q,
  zoom = 12,
  className = '',
  height = 320,
}: GoogleMapEmbedProps) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_EMBED_API_KEY;

  if (!apiKey) {
    return (
      <div
        className={`flex items-center justify-center bg-slate-800 rounded-lg text-slate-400 text-sm ${className}`}
        style={{ height }}
      >
        Google Maps API key not configured
      </div>
    );
  }

  const src = `https://www.google.com/maps/embed/v1/place?key=${apiKey}&q=${encodeURIComponent(q)}&zoom=${zoom}`;

  return (
    <iframe
      title={`Map of ${q}`}
      src={src}
      className={`w-full rounded-lg border border-slate-700 ${className}`}
      style={{ height }}
      allowFullScreen
      loading="lazy"
      referrerPolicy="no-referrer-when-downgrade"
    />
  );
}
