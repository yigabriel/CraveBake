import { api, ApiError } from "../api/client";

/**
 * Photo uploads: shrink in the browser, ask the API for a single-use URL,
 * PUT the file straight to storage (it never goes through our server), and
 * hand back the public URL to register where it belongs.
 */

export type UploadPurpose = "recipe" | "avatar";

interface SignedUpload {
  upload_url: string;
  public_url: string;
  content_type: string;
  max_bytes: number;
}

// Big enough for a full-width cover on a retina laptop; avatars are shown small.
const MAX_SIDE: Record<UploadPurpose, number> = { recipe: 1600, avatar: 512 };
const QUALITY = 0.82;

/** Fits w x h inside a max x max box, keeping the aspect ratio and never enlarging. */
export function fitWithin(width: number, height: number, max: number): { width: number; height: number } {
  const ratio = Math.min(1, max / Math.max(width, height));
  return { width: Math.round(width * ratio), height: Math.round(height * ratio) };
}

/** A phone photo (4+ MB JPEG/HEIC-as-JPEG) becomes a ~200 KB WebP, upright. */
export async function shrinkImage(file: File, purpose: UploadPurpose): Promise<Blob> {
  if (!file.type.startsWith("image/")) throw new UploadError("not_an_image");
  let bitmap: ImageBitmap;
  try {
    // from-image applies the EXIF rotation phones store instead of rotating pixels.
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    throw new UploadError("unreadable");
  }
  const { width, height } = fitWithin(bitmap.width, bitmap.height, MAX_SIDE[purpose]);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new UploadError("unreadable");
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  const toBlob = (type: string) => new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, type, QUALITY));
  // Browsers that cannot encode WebP silently return PNG: fall back to JPEG then.
  const webp = await toBlob("image/webp");
  const blob = webp?.type === "image/webp" ? webp : await toBlob("image/jpeg");
  if (!blob) throw new UploadError("unreadable");
  return blob;
}

export class UploadError extends Error {
  constructor(readonly reason: "not_an_image" | "unreadable" | "too_large" | "failed" | "unavailable") {
    super(reason);
  }
}

function put(url: string, blob: Blob, onProgress?: (fraction: number) => void): Promise<void> {
  // XMLHttpRequest, not fetch: fetch cannot report upload progress.
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("PUT", url);
    request.setRequestHeader("Content-Type", blob.type);
    request.upload.onprogress = (event) => event.lengthComputable && onProgress?.(event.loaded / event.total);
    request.onload = () => (request.status < 300 ? resolve() : reject(new UploadError("failed")));
    request.onerror = () => reject(new UploadError("failed"));
    request.send(blob);
  });
}

/** Shrinks, uploads and returns the photo's public URL. */
export async function uploadImage(file: File, purpose: UploadPurpose, onProgress?: (fraction: number) => void): Promise<string> {
  const blob = await shrinkImage(file, purpose);
  let signed: SignedUpload;
  try {
    signed = await api<SignedUpload>("/media/uploads", { method: "POST", json: { purpose, content_type: blob.type } });
  } catch (error) {
    if (error instanceof ApiError && error.status === 503) throw new UploadError("unavailable");
    throw error;
  }
  if (blob.size > signed.max_bytes) throw new UploadError("too_large");
  await put(signed.upload_url, blob, onProgress);
  return signed.public_url;
}
