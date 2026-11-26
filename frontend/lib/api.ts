import type { CatalogOptions, PreferenceInput, SearchResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  errors: string[];

  constructor(status: number, errors: string[]) {
    super(errors[0] ?? "The request failed.");
    this.status = status;
    this.errors = errors.length > 0 ? errors : ["The request failed."];
  }
}

export async function loadOptions(): Promise<CatalogOptions> {
  const health = await request("/api/health");
  const healthBody = health.body;
  const catalogLoaded =
    health.status === 200 &&
    isRecord(healthBody) &&
    healthBody.catalog_loaded === true;
  if (!catalogLoaded) {
    throw new ApiError(503, ["The catalog is not available."]);
  }
  const options = await request("/api/options");
  if (options.status !== 200 || !isCatalogOptions(options.body)) {
    throw new ApiError(options.status, errorsFrom(options.body));
  }
  return options.body;
}

export async function recommend(input: PreferenceInput): Promise<SearchResponse> {
  const notes = input.notes.trim();
  const payload: Record<string, unknown> = {
    location: input.location,
    budget: input.budget,
    cuisine: input.cuisine,
    min_rating: Number(input.minRating),
  };
  if (notes) {
    payload.notes = notes;
  }
  const response = await request("/api/recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (response.status !== 200 || !isSearchResponse(response.body)) {
    throw new ApiError(response.status, errorsFrom(response.body));
  }
  return response.body;
}

async function request(path: string, init?: RequestInit): Promise<{ status: number; body: unknown }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, ["The recommendation API is not reachable."]);
  }
  const text = await response.text();
  if (!text) {
    return { status: response.status, body: {} };
  }
  try {
    return { status: response.status, body: JSON.parse(text) as unknown };
  } catch {
    throw new ApiError(response.status, ["The recommendation API returned an unreadable response."]);
  }
}

function isRecord(body: unknown): body is Record<string, unknown> {
  return body !== null && typeof body === "object";
}

function errorsFrom(body: unknown): string[] {
  if (isRecord(body) && Array.isArray(body.errors)) {
    const messages = body.errors.filter((item): item is string => typeof item === "string" && item.trim() !== "");
    if (messages.length > 0) {
      return messages;
    }
  }
  return ["The search could not be completed."];
}

function isCatalogOptions(body: unknown): body is CatalogOptions {
  if (!body || typeof body !== "object") {
    return false;
  }
  const value = body as CatalogOptions;
  return Array.isArray(value.locations) && Array.isArray(value.cuisines) && Array.isArray(value.budgets);
}

function isSearchResponse(body: unknown): body is SearchResponse {
  if (!body || typeof body !== "object") {
    return false;
  }
  return Array.isArray((body as SearchResponse).recommendations);
}
