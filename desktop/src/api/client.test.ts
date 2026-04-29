import { describe, it, expect, beforeEach } from "vitest";
import client, { setBaseURL, getBaseURL } from "@/api/client";

describe("API client", () => {
  beforeEach(() => {
    // Reset to default after each test
    setBaseURL(8000);
  });

  describe("given setBaseURL is called with port 9000", () => {
    it("should return the new URL from getBaseURL", () => {
      setBaseURL(9000);
      expect(getBaseURL()).toBe("http://127.0.0.1:9000");
    });

    it("should update the axios instance baseURL", () => {
      setBaseURL(9000);
      expect(client.defaults.baseURL).toBe("http://127.0.0.1:9000");
    });
  });

  describe("given the default state", () => {
    it("should use port 8000 as default", () => {
      expect(getBaseURL()).toBe("http://127.0.0.1:8000");
    });
  });
});
