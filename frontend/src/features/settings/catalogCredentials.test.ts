import { expect, it } from "vitest";
import { catalogRequestIdentity } from "./catalogCredentials";

it("invalidates a directory when connection or credentials change", () => {
  const request = { provider: "LocalAiMux", base_url: "http://127.0.0.1:8317/v1", connection_type: "LOCAL_ROUTER" as const, api_key: "", profile_id: undefined };
  for (const change of [{ provider: "Custom" }, { base_url: "http://other.test/v1" }, { connection_type: "DIRECT" as const }, { api_key: "new-key" }, { profile_id: "saved" }]) {
    expect(catalogRequestIdentity({ ...request, ...change })).not.toBe(catalogRequestIdentity(request));
  }
});
