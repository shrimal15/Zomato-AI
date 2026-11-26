import type { BudgetBand } from "./types";

export const FALLBACK_NOTICE = "These matches use catalog facts. An AI explanation was not produced.";
export const NO_EXPLANATION = "No AI explanation was produced.";

export function formatRating(rating: number): string {
  return Number(rating.toFixed(1)).toString();
}

export function ratingChoices(min: number, max: number): string[] {
  const start = Math.round(min * 10);
  const end = Math.round(max * 10);
  const choices: string[] = [];
  for (let step = start; step <= end; step += 1) {
    choices.push((step / 10).toFixed(1));
  }
  return choices;
}

export function budgetLabel(band: BudgetBand): string {
  const name = band.id.charAt(0).toUpperCase() + band.id.slice(1);
  if (band.max !== undefined && band.min_exclusive === undefined) {
    return `${name} · up to ₹${band.max}`;
  }
  if (band.min_exclusive !== undefined && band.max !== undefined) {
    return `${name} · ₹${band.min_exclusive + 1}–₹${band.max}`;
  }
  if (band.min_exclusive !== undefined) {
    return `${name} · above ₹${band.min_exclusive}`;
  }
  return name;
}

export function resultHeading(count: number): string {
  return count === 1 ? "1 recommendation" : `${count} recommendations`;
}
