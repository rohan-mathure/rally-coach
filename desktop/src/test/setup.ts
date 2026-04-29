import "@testing-library/jest-dom";
import { vi } from "vitest";

// Stub Electron bridge for all renderer tests.
Object.defineProperty(window, "electronAPI", {
  value: {
    getServerPort: vi.fn().mockResolvedValue(8000),
    onServerReady: vi.fn(),
    openFileDialog: vi.fn().mockResolvedValue("/tmp/test.mp4"),
    getUserDataPath: vi.fn().mockResolvedValue("/tmp"),
    openExternal: vi.fn(),
  },
  writable: true,
});
