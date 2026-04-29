import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KPIStrip } from "@/components/KPIStrip";
import type { Session, Shot } from "@/types";

const session: Session = {
  session_id: "s1",
  filename: "match.mp4",
  uploaded_at: "2024-01-01T00:00:00Z",
  status: "complete",
  total_shots: 10,
  avg_speed_mph: 65,
};

const makeShot = (overrides: Partial<Shot> = {}): Shot => ({
  shot_id: Math.random().toString(),
  session_id: "s1",
  shot_number: 1,
  start_frame: 0,
  end_frame: 50,
  contact_frame: 10,
  start_time_sec: 0,
  trajectory: [],
  shot_type: "forehand",
  shot_type_confidence: 0.9,
  spin_type: "flat",
  spin_confidence: 0.7,
  speed_confidence: 0.8,
  is_in: true,
  is_close_call: false,
  detection_gap_frames: 0,
  pipeline_warnings: [],
  ...overrides,
});

describe("KPIStrip", () => {
  describe("given a session with avg_speed_mph", () => {
    it("displays the avg speed", () => {
      render(<KPIStrip session={session} shots={[]} />);
      expect(screen.getByText(/65 mph/)).toBeInTheDocument();
    });
  });

  describe("given shots with mixed in/out results", () => {
    it("computes in-bounds percentage", () => {
      const shots = [
        makeShot({ is_in: true }),
        makeShot({ is_in: true }),
        makeShot({ is_in: false }),
        makeShot({ is_in: false }),
      ];
      render(<KPIStrip session={session} shots={shots} />);
      expect(screen.getByText("50%")).toBeInTheDocument();
    });
  });

  describe("given no shots", () => {
    it("shows dash for in-bounds percentage", () => {
      render(<KPIStrip session={session} shots={[]} />);
      const dashes = screen.getAllByText("—");
      expect(dashes.length).toBeGreaterThan(0);
    });
  });
});
