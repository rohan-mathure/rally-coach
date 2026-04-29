import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "@/components/StatusBadge";
import type { SessionStatus } from "@/types";

const STATUSES: SessionStatus[] = ["queued", "processing", "complete", "error"];

describe("StatusBadge", () => {
  describe.each(STATUSES)("given status '%s'", (status) => {
    it("renders a span with the status text", () => {
      render(<StatusBadge status={status} />);
      const badge = screen.getByText(new RegExp(status, "i"));
      expect(badge).toBeInTheDocument();
    });

    it("applies the status-specific CSS class", () => {
      const { container } = render(<StatusBadge status={status} />);
      const span = container.querySelector("span");
      expect(span?.className).toContain(`badge-${status}`);
    });
  });
});
