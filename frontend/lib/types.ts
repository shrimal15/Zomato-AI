export type BudgetBand = {
  id: string;
  max?: number;
  min_exclusive?: number;
};

export type CatalogOptions = {
  locations: string[];
  cuisines: string[];
  rating_min: number;
  rating_max: number;
  budgets: BudgetBand[];
};

export type RecommendationCard = {
  id: string;
  name: string;
  cuisines: string[];
  rating: number;
  cost_for_two: number;
  explanation: string | null;
};

export type SearchResponse = {
  location: string;
  budget: string;
  cuisine: string;
  min_rating: number;
  notes: string | null;
  recommendations: RecommendationCard[];
  explanations_available: boolean;
  model_called: boolean;
  summary?: string;
  empty_message?: string;
};

export type PreferenceInput = {
  location: string;
  budget: string;
  cuisine: string;
  minRating: string;
  notes: string;
};
