import { describe, expect, it } from "vitest";
import { getSafeAdminUrl } from "./urls";

describe("getSafeAdminUrl", () => {
  it("accepts HTTP and HTTPS admin URLs", () => {
    expect(getSafeAdminUrl("https://tracker.example/admin")).toBe(
      "https://tracker.example/admin",
    );
    expect(getSafeAdminUrl("http://localhost:8080/admin")).toBe(
      "http://localhost:8080/admin",
    );
  });

  it("rejects script and non-web URL schemes", () => {
    expect(getSafeAdminUrl("javascript:alert(1)")).toBeNull();
    expect(getSafeAdminUrl("data:text/html,unsafe")).toBeNull();
  });

  it("rejects malformed URLs and embedded credentials", () => {
    expect(getSafeAdminUrl("not a URL")).toBeNull();
    expect(getSafeAdminUrl("https://user:pass@tracker.example/admin")).toBeNull();
  });
});
