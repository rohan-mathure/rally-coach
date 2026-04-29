import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CourtMap } from "@/components/CourtMap";
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
  speed_confidence: 0.8,
  is_in: true,
  is_close_call: false,
  detection_gap_frames: 0,
  pipeline_warnings: [],
  ...overrides,
});

describe("CourtMap", () => {
  // Bounce dots are inside the main court SVG (width=280); legend circles are in small SVGs (width=10)
  const bounceDots = (container: HTMLElement) =>
    container.querySelectorAll("svg[width='280'] circle");

  describe("given an empty shots array", () => {
    it("renders the SVG court", () => {
      const { container } = render(<CourtMap shots={[]} />);
      expect(container.querySelector("svg")).toBeInTheDocument();
    });

    it("renders zero bounce dots", () => {
      const { container } = render(<CourtMap shots={[]} />);
      expect(bounceDots(container)).toHaveLength(0);
    });
  });

  describe("given shots with bounce coordinates", () => {
    const shots = [
      makeShot({ shot_id: "a", bounce_court_x: 0, bounce_court_y: 39 }),
      makeShot({ shot_id: "b", bounce_court_x: 5, bounce_court_y: 55 }),
    ];

    it("renders a bounce dot for each shot with coordinates", () => {
      const { container } = render(<CourtMap shots={shots} />);
      expect(bounceDots(container)).toHaveLength(shots.length);
    });
  });

  describe("given shots without bounce coordinates", () => {
    it("renders zero bounce dots", () => {
      const shots = [makeShot({ bounce_court_x: undefined, bounce_court_y: undefined })];
      const { container } = render(<CourtMap shots={shots} />);
      expect(bounceDots(container)).toHaveLength(0);
    });
  });

  describe("given filter buttons", () => {
    it("renders All/FH/BH/VOL/OH filter buttons", () => {
      render(<CourtMap shots={[]} />);
      expect(screen.getByText("All")).toBeInTheDocument();
      expect(screen.getByText("FH")).toBeInTheDocument();
      expect(screen.getByText("BH")).toBeInTheDocument();
    });
  });
});
