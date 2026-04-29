import { describe, it, expect, beforeEach, afterAll } from "vitest";
import MockAdapter from "axios-mock-adapter";
import client from "@/api/client";
import {
  listSessions,
  getSession,
  uploadSession,
  listShots,
  getVideoUrl,
  getCsvUrl,
} from "@/api/sessions";
import type { Session, Shot } from "@/types";

const mock = new MockAdapter(client);

afterAll(() => mock.restore());
beforeEach(() => mock.reset());

const sampleSession: Session = {
  session_id: "sess-1",
  filename: "match.mp4",
  uploaded_at: "2024-01-01T00:00:00Z",
  status: "complete",
  total_shots: 5,
  avg_speed_mph: 72,
};

const sampleShot: Shot = {
  shot_id: "shot-1",
  session_id: "sess-1",
  shot_number: 1,
  start_frame: 100,
  end_frame: 150,
  contact_frame: 110,
  start_time_sec: 1.0,
  trajectory: [],
  shot_type: "forehand",
  shot_type_confidence: 0.9,
  spin_type: "topspin",
  spin_confidence: 0.8,
  speed_mph: 75,
  speed_confidence: 0.85,
  is_in: true,
  is_close_call: false,
  detection_gap_frames: 0,
  pipeline_warnings: [],
};

describe("Sessions API", () => {
  describe("given a running server", () => {
    it("should return an array of sessions on listSessions", async () => {
      mock.onGet("/api/sessions").reply(200, [sampleSession]);
      const sessions = await listSessions();
      expect(sessions).toHaveLength(1);
      expect(sessions[0].session_id).toBe("sess-1");
    });

    it("should return a single session on getSession", async () => {
      mock.onGet("/api/sessions/sess-1").reply(200, sampleSession);
      const session = await getSession("sess-1");
      expect(session.session_id).toBe("sess-1");
      expect(session.status).toBe("complete");
    });

    it("should throw on 404 getSession", async () => {
      mock.onGet("/api/sessions/bad-id").reply(404, { detail: "Not found" });
      await expect(getSession("bad-id")).rejects.toThrow();
    });

    it("should POST from-path and return session_id on uploadSession", async () => {
      mock
        .onPost("/api/sessions/from-path")
        .reply(201, { session_id: "new-sess", status: "queued" });
      const result = await uploadSession("/tmp/video.mp4");
      expect(result.session_id).toBe("new-sess");
      expect(result.status).toBe("queued");
    });

    it("should return shots array on listShots", async () => {
      mock.onGet("/api/sessions/sess-1/shots").reply(200, [sampleShot]);
      const shots = await listShots("sess-1");
      expect(shots).toHaveLength(1);
      expect(shots[0].shot_type).toBe("forehand");
    });

    it("should construct correct video URL from getVideoUrl", () => {
      const url = getVideoUrl("sess-1");
      expect(url).toContain("/api/sessions/sess-1/video");
    });

    it("should construct correct CSV URL from getCsvUrl", () => {
      const url = getCsvUrl("sess-1");
      expect(url).toContain("/api/sessions/sess-1/shots/csv");
    });
  });
});
