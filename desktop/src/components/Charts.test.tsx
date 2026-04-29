import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { ShotTypeChart, SpinTypeChart, SpeedHistogram, QualityHistogram } from "@/components/Charts";
import type { Shot } from "@/types";

// recharts ResponsiveContainer requires layout measurements jsdom can't provide.
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="chart-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => <svg>{children}</svg>,
  PieChart: ({ children }: { children: React.ReactNode }) => <svg>{children}</svg>,
  Bar: () => null,
  Pie: () => null,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

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
  speed_mph: 70,
  speed_confidence: 0.8,
  quality_score: 80,
  is_in: true,
  is_close_call: false,
  detection_gap_frames: 0,
  pipeline_warnings: [],
  ...overrides,
});

const shots = [
  makeShot({ shot_type: "forehand", spin_type: "topspin", speed_mph: 65, quality_score: 75 }),
  makeShot({ shot_type: "backhand", spin_type: "flat", speed_mph: 80, quality_score: 90 }),
  makeShot({ shot_type: "volley", spin_type: "underspin", speed_mph: 50, quality_score: 60 }),
];

describe("Charts", () => {
  describe("ShotTypeChart", () => {
    describe("given shots with different shot types", () => {
      it("renders without error", () => {
        const { container } = render(<ShotTypeChart shots={shots} />);
        expect(container.querySelector("[data-testid='chart-container']")).toBeInTheDocument();
      });
    });

    describe("given an empty shots array", () => {
      it("renders without error", () => {
        const { container } = render(<ShotTypeChart shots={[]} />);
        expect(container).toBeInTheDocument();
      });
    });
  });

  describe("SpinTypeChart", () => {
    describe("given shots with different spin types", () => {
      it("renders without error", () => {
        const { container } = render(<SpinTypeChart shots={shots} />);
        expect(container.querySelector("[data-testid='chart-container']")).toBeInTheDocument();
      });
    });
  });

  describe("SpeedHistogram", () => {
    describe("given shots with speed data", () => {
      it("renders without error", () => {
        const { container } = render(<SpeedHistogram shots={shots} />);
        expect(container.querySelector("[data-testid='chart-container']")).toBeInTheDocument();
      });
    });

    describe("given shots with no speed data", () => {
      it("renders without error", () => {
        const noSpeed = [makeShot({ speed_mph: undefined })];
        const { container } = render(<SpeedHistogram shots={noSpeed} />);
        expect(container).toBeInTheDocument();
      });
    });
  });

  describe("QualityHistogram", () => {
    describe("given shots with quality scores", () => {
      it("renders without error", () => {
        const { container } = render(<QualityHistogram shots={shots} />);
        expect(container.querySelector("[data-testid='chart-container']")).toBeInTheDocument();
      });
    });
  });
});
