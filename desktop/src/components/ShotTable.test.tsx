import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ShotTable } from "@/components/ShotTable";
import type { Shot } from "@/types";

const makeShot = (overrides: Partial<Shot> = {}): Shot => ({
  shot_id: `shot-${Math.random()}`,
  session_id: "s1",
  shot_number: 1,
  start_frame: 0,
  end_frame: 50,
  contact_frame: 10,
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
  ...overrides,
});

describe("ShotTable", () => {
  describe("given an empty shots array", () => {
    it("renders zero data rows", () => {
      const { container } = render(<ShotTable shots={[]} />);
      const rows = container.querySelectorAll("tbody tr");
      expect(rows).toHaveLength(0);
    });
  });

  describe("given shots with mixed in/out results", () => {
    const shots = [
      makeShot({ shot_id: "a", shot_number: 1, is_in: true, is_close_call: false }),
      makeShot({ shot_id: "b", shot_number: 2, is_in: false, is_close_call: false }),
      makeShot({ shot_id: "c", shot_number: 3, is_in: true, is_close_call: true }),
    ];

    it("renders 'In' label for in-bounds shot", () => {
      render(<ShotTable shots={shots} />);
      expect(screen.getByText("In")).toBeInTheDocument();
    });

    it("renders 'Out' label for out-of-bounds shot", () => {
      render(<ShotTable shots={shots} />);
      expect(screen.getByText("Out")).toBeInTheDocument();
    });

    it("renders 'Close' label for close-call shot", () => {
      render(<ShotTable shots={shots} />);
      expect(screen.getByText("Close")).toBeInTheDocument();
    });

    it("displays formatted speed in mph", () => {
      render(<ShotTable shots={shots} />);
      const speedCells = screen.getAllByText(/75 mph/);
      expect(speedCells.length).toBeGreaterThan(0);
    });
  });

  describe("given a shot with null speed", () => {
    it("displays '—' for null speed", () => {
      render(<ShotTable shots={[makeShot({ speed_mph: undefined })]} />);
      const dashes = screen.getAllByText("—");
      expect(dashes.length).toBeGreaterThan(0);
    });
  });

  describe("given user clicks a column header", () => {
    it("sorts shots by that column ascending on first click", async () => {
      const user = userEvent.setup();
      const shots = [
        makeShot({ shot_id: "x", shot_number: 3, speed_mph: 50 }),
        makeShot({ shot_id: "y", shot_number: 1, speed_mph: 90 }),
        makeShot({ shot_id: "z", shot_number: 2, speed_mph: 70 }),
      ];
      const { container } = render(<ShotTable shots={shots} />);
      await user.click(screen.getByText(/Speed/));
      const rows = container.querySelectorAll("tbody tr");
      // After sort by speed asc: 50, 70, 90
      expect(rows[0].textContent).toContain("50");
      expect(rows[2].textContent).toContain("90");
    });
  });

  describe("given user clicks a shot row", () => {
    it("calls onSelectShot with the clicked shot", async () => {
      const user = userEvent.setup();
      const onSelect = vi.fn();
      const shot = makeShot({ shot_id: "test-shot" });
      render(<ShotTable shots={[shot]} onSelectShot={onSelect} />);
      await user.click(screen.getAllByRole("row")[1]); // first data row
      expect(onSelect).toHaveBeenCalledWith(shot);
    });
  });
});
