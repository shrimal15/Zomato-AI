"use client";

import { useEffect, useState } from "react";

import { ApiError, loadOptions, recommend } from "../lib/api";
import type { CatalogOptions, PreferenceInput, SearchResponse } from "../lib/types";
import { PreferenceForm } from "./preference-form";
import { Results } from "./results";

const EMPTY_INPUT: PreferenceInput = {
  location: "",
  budget: "",
  cuisine: "",
  minRating: "",
  notes: "",
};

export function SearchScreen() {
  const [options, setOptions] = useState<CatalogOptions | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [values, setValues] = useState<PreferenceInput>(EMPTY_INPUT);
  const [errors, setErrors] = useState<string[]>([]);
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadOptions()
      .then((loaded) => {
        if (!cancelled) {
          setOptions(loaded);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(error instanceof ApiError ? error.message : "The catalog is not available.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit() {
    setSearching(true);
    setErrors([]);
    setResult(null);
    try {
      setResult(await recommend(values));
    } catch (error: unknown) {
      if (error instanceof ApiError) {
        setErrors(error.errors);
      } else {
        setErrors(["The search could not be completed."]);
      }
    } finally {
      setSearching(false);
    }
  }

  const subtitle = loadError
    ? loadError
    : searching
      ? "Finding a short list of restaurants…"
      : result?.empty_message
        ? result.empty_message
        : result?.summary
          ? result.summary
          : result
            ? null
            : "Set a neighborhood, budget, cuisine, and rating.";

  return (
    <>
      <h1>Find a restaurant · Zomato AI</h1>
      {subtitle ? <p className="subtitle">{subtitle}</p> : null}
      {result && !searching ? <Results result={result} /> : null}
      {options ? (
        <PreferenceForm
          options={options}
          values={values}
          errors={errors}
          disabled={searching}
          onChange={setValues}
          onSubmit={onSubmit}
        />
      ) : null}
    </>
  );
}
