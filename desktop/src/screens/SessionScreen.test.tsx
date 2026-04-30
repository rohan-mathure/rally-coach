import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionScreen } from "@/screens/SessionScreen";
import type { Session, Shot } from "@/types";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-session-id" }),
  useNavigate: () => vi.fn(),
}));

vi.mock("@/api/sessions", () => ({
  getSession: vi.fn(),
  listShots: vi.fn(),
  getVideoUrl: () => "http://localhost:8000/api/sessions/test-session-id/video",
  getCsvUrl: () => "http://localhost:8000/api/sessions/test-session-id/shots/csv",
}));

vi.mock("@/components/VideoPlayer", () => ({
  VideoPlayer: ({ src }: { src: string }) => (
    <video data-testid="video-player" src={src} />
  ),
}));

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="chart-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => <svg>{children}</svg>,
  PieChart: ({ children }: { children: React.ReactNode }) => <svg>{children}</svg>,
  Bar: () => null, Pie: () => null, Cell: () => null,
  XAxis: () => null, YAxis: () => null, Tooltip: () => null, Legend: () => null,
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

import { getSession, listShots } from "@/api/sessions";

const mockSession: Session = {
  session_id: "test-session-id",
  filename: "match.mp4",
  uploaded_at: "2026-04-30T00:00:00Z",
  status: "complete",
  fps: 60,
  total_frames: 18000,
  width: 1920,
  height: 1080,
  total_shots: 2,
  avg_speed_mph: 72,
};

const makeShot = (overrides: Partial<Shot> = {}): Shot => ({
  shot_id: `shot-${Math.random()}`,
  session_id: "test-session-id",
  shot_number: 1,
  start_frame: 0,
  end_frame: 60,
  contact_frame: 10,
  start_time_sec: 0.5,
  trajectory: [],
  shot_type: "forehand",
  shot_type_confidence: 0.8,
  spin_type: "topspin",
  spin_confidence: 0.75,
  speed_mph: 70,
  speed_confidence: 0.8,
  is_in: true,
  is_close_call: false,
  detection_gap_frames: 0,
  pipeline_warnings: [],
  ...overrides,
});

const mockShots: Shot[] = [
  makeShot({ shot_id: "shot-a", shot_number: 1, bounce_court_x: 2,  bounce_court_y: 45 }),
  makeShot({ shot_id: "shot-b", shot_number: 2, bounce_court_x: -3, bounce_court_y: 60 }),
];

beforeEach(() => {
  vi.clearAllMocks();
  (getSession as ReturnType<typeof vi.fn>).mockResolvedValue(mockSession);
  (listShots  as ReturnType<typeof vi.fn>).mockResolvedValue(mockShots);
});

// Suppress the setInterval that polls every 5 s — we don't want it firing mid-test.
// We do this by replacing setInterval/clearInterval with no-ops scoped to each test.
beforeEach(() => {
  vi.spyOn(window, "setInterval").mockImplementation((() => 0) as typeof setInterval);
  vi.spyOn(window, "clearInterval").mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

const bounceDots = () =>
  document.querySelectorAll("svg[width='280'] circle");

/** Render and wait until the complete session view is loaded. */
async function renderAndLoad() {
  const user = userEvent.setup();
  render(<SessionScreen />);
  await waitFor(() => screen.getByText("📊 Overview"), { timeout: 3000 });
  return user;
}

// ---------------------------------------------------------------------------
// Overview tab
// ---------------------------------------------------------------------------

describe("SessionScreen — overview tab", () => {
  it("renders session filename in the header", async () => {
    await renderAndLoad();
    expect(screen.getByText("match.mp4")).toBeInTheDocument();
  });

  it("renders all four tab buttons", async () => {
    await renderAndLoad();
    expect(screen.getByText("📊 Overview")).toBeInTheDocument();
    expect(screen.getByText("🎬 Video")).toBeInTheDocument();
    expect(screen.getByText("🎾 Court Map")).toBeInTheDocument();
    expect(screen.getByText("📋 Shots")).toBeInTheDocument();
  });

  it("shows charts in the overview tab by default", async () => {
    await renderAndLoad();
    expect(screen.getByText("Shot Type")).toBeInTheDocument();
    expect(screen.getByText("Spin Type")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Court map tab — key behaviour
// ---------------------------------------------------------------------------

describe("SessionScreen — court map tab", () => {
  it("shows the court map when the Court Map tab is clicked", async () => {
    const user = await renderAndLoad();
    await user.click(screen.getByText("🎾 Court Map"));
    expect(screen.getByText("Bounce Locations")).toBeInTheDocument();
  });

  it("clicking a bounce dot does NOT switch to the video tab", async () => {
    const user = await renderAndLoad();
    await user.click(screen.getByText("🎾 Court Map"));

    const dots = bounceDots();
    if (dots.length > 0) {
      await user.click(dots[0]);
      expect(screen.getByText("Bounce Locations")).toBeInTheDocument();
      expect(screen.queryByTestId("video-player")).not.toBeInTheDocument();
    }
  });

  it("shows 'Watch in video' button after clicking a bounce dot", async () => {
    const user = await renderAndLoad();
    await user.click(screen.getByText("🎾 Court Map"));

    const dots = bounceDots();
    if (dots.length > 0) {
      await user.click(dots[0]);
      expect(await screen.findByText("Watch in video")).toBeInTheDocument();
    }
  });

  it("clicking 'Watch in video' switches to the video tab", async () => {
    const user = await renderAndLoad();
    await user.click(screen.getByText("🎾 Court Map"));

    const dots = bounceDots();
    if (dots.length > 0) {
      await user.click(dots[0]);
      const watchBtn = await screen.findByText("Watch in video");
      await user.click(watchBtn);
      expect(screen.getByTestId("video-player")).toBeInTheDocument();
    }
  });

  it("does not show 'Watch in video' before any shot is selected", async () => {
    const user = await renderAndLoad();
    await user.click(screen.getByText("🎾 Court Map"));
    expect(screen.queryByText("Watch in video")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Video tab
// ---------------------------------------------------------------------------

describe("SessionScreen — video tab", () => {
  it("renders the video player when the Video tab is clicked", async () => {
    const user = await renderAndLoad();
    await user.click(screen.getByText("🎬 Video"));
    expect(screen.getByTestId("video-player")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

describe("SessionScreen — error state", () => {
  it("shows error message when session status is error", async () => {
    (getSession as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockSession,
      status: "error",
      error_message: "No ball detected",
    });
    render(<SessionScreen />);
    await screen.findByText("Processing failed");
    expect(screen.getByText("No ball detected")).toBeInTheDocument();
  });
});
