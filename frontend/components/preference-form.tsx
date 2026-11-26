import { budgetLabel, formatRating, ratingChoices } from "../lib/format";
import type { CatalogOptions, PreferenceInput } from "../lib/types";

type PreferenceFormProps = {
  options: CatalogOptions;
  values: PreferenceInput;
  errors: string[];
  disabled: boolean;
  onChange: (values: PreferenceInput) => void;
  onSubmit: () => void;
};

export function PreferenceForm({
  options,
  values,
  errors,
  disabled,
  onChange,
  onSubmit,
}: PreferenceFormProps) {
  function update(patch: Partial<PreferenceInput>) {
    onChange({ ...values, ...patch });
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      {errors.length > 0 ? (
        <ul className="errors" role="alert">
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
      <fieldset disabled={disabled}>
        <div className="form-grid">
          <div className="stack">
            <div className="field">
              <label htmlFor="location">Location</label>
              <select
                id="location"
                name="location"
                required
                value={values.location}
                onChange={(event) => update({ location: event.target.value })}
              >
                <option value="">Choose a neighborhood</option>
                {options.locations.map((location) => (
                  <option key={location} value={location}>
                    {location}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="budget">Budget</label>
              <select
                id="budget"
                name="budget"
                required
                value={values.budget}
                onChange={(event) => update({ budget: event.target.value })}
              >
                <option value="">Choose a budget</option>
                {options.budgets.map((band) => (
                  <option key={band.id} value={band.id}>
                    {budgetLabel(band)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="stack">
            <div className="field">
              <label htmlFor="cuisine">Cuisine</label>
              <select
                id="cuisine"
                name="cuisine"
                required
                value={values.cuisine}
                onChange={(event) => update({ cuisine: event.target.value })}
              >
                <option value="">Choose a cuisine</option>
                {options.cuisines.map((cuisine) => (
                  <option key={cuisine} value={cuisine}>
                    {cuisine}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="min_rating">Minimum rating</label>
              <select
                id="min_rating"
                name="min_rating"
                required
                value={values.minRating}
                onChange={(event) => update({ minRating: event.target.value })}
              >
                <option value="">Choose a rating</option>
                {ratingChoices(options.rating_min, options.rating_max).map((rating) => (
                  <option key={rating} value={rating}>
                    {rating} ★
                  </option>
                ))}
              </select>
              <span className="hint">
                Catalog ratings {formatRating(options.rating_min)} to {formatRating(options.rating_max)}
              </span>
            </div>
          </div>
        </div>
        <div className="notes-row">
          <div className="field">
            <label htmlFor="notes">Other preferences</label>
            <textarea
              id="notes"
              name="notes"
              maxLength={500}
              placeholder="Family-friendly, quick service"
              value={values.notes}
              onChange={(event) => update({ notes: event.target.value })}
            />
          </div>
          <button type="submit">{disabled ? "Finding restaurants…" : "Find with Zomato AI"}</button>
        </div>
      </fieldset>
    </form>
  );
}
