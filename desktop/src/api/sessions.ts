import client, { getBaseURL } from "./client";
import { Session, Shot } from "@/types";

export async function listSessions(): Promise<Session[]> {
  const { data } = await client.get<Session[]>("/api/sessions");
  return data;
}

export async function getSession(id: string): Promise<Session> {
  const { data } = await client.get<Session>(`/api/sessions/${id}`);
  return data;
}

export async function uploadSession(
  filePath: string,
  onProgress?: (pct: number) => void
): Promise<{ session_id: string; status: string }> {
  // In Electron, we have the file path. Send it to the backend using a
  // special endpoint that accepts a local path (avoids streaming large files).
  const { data } = await client.post(
    "/api/sessions/from-path",
    { path: filePath },
    {
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    }
  );
  return data;
}

export async function uploadSessionFile(
  file: File,
  onProgress?: (pct: number) => void
): Promise<{ session_id: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post("/api/sessions", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return data;
}

export async function listShots(sessionId: string): Promise<Shot[]> {
  const { data } = await client.get<Shot[]>(`/api/sessions/${sessionId}/shots`);
  return data;
}

export function getVideoUrl(sessionId: string): string {
  return `${getBaseURL()}/api/sessions/${sessionId}/video`;
}

export function getCsvUrl(sessionId: string): string {
  return `${getBaseURL()}/api/sessions/${sessionId}/shots/csv`;
}
