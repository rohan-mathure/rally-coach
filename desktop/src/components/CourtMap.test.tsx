import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

/** Circles inside the main court SVG (width=280), excluding the legend's small SVGs. */
const bounceDots = (container: HTMLElement) =>
  container.querySelectorAll("svg[width='280'] circle");

describe("CourtMap", () => {
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

  describe("given onSelectShot callback", () => {
    it("calls onSelectShot with the correct shot when a dot is clicked", async () => {
      const user = userEvent.setup();
      const onSelectShot = vi.fn();
      const shot = makeShot({ shot_id: "target", bounce_court_x: 0, bounce_court_y: 45 });
      const { container } = render(
        <CourtMap shots={[shot]} onSelectShot={onSelectShot} />
      );

      const dot = bounceDots(container)[0];
      await user.click(dot!);

      expect(onSelectShot).toHaveBeenCalledOnce();
      expect(onSelectShot).toHaveBeenCalledWith(expect.objectContaining({ shot_id: "target" }));
    });

    it("does not throw when onSelectShot is not provided", async () => {
      const user = userEvent.setup();
      const shot = makeShot({ shot_id: "no-cb", bounce_court_x: 0, bounce_court_y: 45 });
      const { container } = render(<CourtMap shots={[shot]} />);
      const dot = bounceDots(container)[0];
      await expect(user.click(dot!)).resolves.not.toThrow();
    });
  });

  describe("given activeShot prop", () => {
    const shots = [
      makeShot({ shot_id: "active-one", bounce_court_x: 2, bounce_court_y: 45 }),
      makeShot({ shot_id: "inactive",   bounce_court_x: -3, bounce_court_y: 60 }),
    ];

    it("gives the active dot a white stroke", () => {
      const { container } = render(
        <CourtMap shots={shots} activeShot="active-one" />
      );
      const dots = Array.from(bounceDots(container));
      const activeDot = dots.find((d) => d.getAttribute("stroke") === "#fff");
      expect(activeDot).toBeInTheDocument();
    });

    it("gives the active dot a strokeWidth of 2", () => {
      const { container } = render(
        <CourtMap shots={shots} activeShot="active-one" />
      );
      const dots = Array.from(bounceDots(container));
      const activeDot = dots.find((d) => d.getAttribute("stroke-width") === "2");
      expect(activeDot).toBeInTheDocument();
    });

    it("other dots keep strokeWidth of 1", () => {
      const { container } = render(
        <CourtMap shots={shots} activeShot="active-one" />
      );
      const dots = Array.from(bounceDots(container));
      const inactive = dots.filter((d) => d.getAttribute("stroke-width") === "1");
      expect(inactive).toHaveLength(1);
    });

    it("no dot has white stroke when activeShot is undefined", () => {
      const { container } = render(<CourtMap shots={shots} />);
      const dots = Array.from(bounceDots(container));
      const whiteDot = dots.find((d) => d.getAttribute("stroke") === "#fff");
      expect(whiteDot).toBeUndefined();
    });
  });

  describe("given filter interaction", () => {
    const shots = [
      makeShot({ shot_id: "fh", shot_type: "forehand", bounce_court_x: 2, bounce_court_y: 45 }),
      makeShot({ shot_id: "bh", shot_type: "backhand", bounce_court_x: -2, bounce_court_y: 55 }),
    ];

    it("shows all shots when 'All' is active", () => {
      const { container } = render(<CourtMap shots={shots} />);
      expect(bounceDots(container)).toHaveLength(2);
    });

    it("filters to only forehand shots when FH is clicked", async () => {
      const user = userEvent.setup();
      const { container } = render(<CourtMap shots={shots} />);
      await user.click(screen.getByText("FH"));
      expect(bounceDots(container)).toHaveLength(1);
    });

    it("filters to only backhand shots when BH is clicked", async () => {
      const user = userEvent.setup();
      const { container } = render(<CourtMap shots={shots} />);
      await user.click(screen.getByText("BH"));
      expect(bounceDots(container)).toHaveLength(1);
    });

    it("shows no dots when VOL is clicked and there are no volleys", async () => {
      const user = userEvent.setup();
      const { container } = render(<CourtMap shots={shots} />);
      await user.click(screen.getByText("VOL"));
      expect(bounceDots(container)).toHaveLength(0);
    });
  });

  describe("given hover interaction", () => {
    it("shows tooltip on hover with shot number and type", async () => {
      const user = userEvent.setup();
      const shot = makeShot({
        shot_id: "h1",
        shot_number: 7,
        shot_type: "forehand",
        spin_type: "topspin",
        speed_mph: 85,
        bounce_court_x: 0,
        bounce_court_y: 45,
      });
      const { container } = render(<CourtMap shots={[shot]} />);
      const dot = bounceDots(container)[0];
      await user.hover(dot!);
      expect(screen.getByText(/#7/)).toBeInTheDocument();
    });
  });
});
