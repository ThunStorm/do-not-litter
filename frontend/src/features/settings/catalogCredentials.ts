import type { ModelProfileView } from "../../lib/types";

type Connection = Pick<ModelProfileView, "provider" | "base_url"> & { connection_type?: ModelProfileView["connection_type"] };
type CatalogRequest = Connection & { api_key: string; profile_id?: string };

export function catalogRequestIdentity(request: CatalogRequest) {
  return JSON.stringify([request.provider, request.base_url, request.connection_type, request.api_key, request.profile_id]);
}
