import { FALLBACK_NOTICE, NO_EXPLANATION, formatRating } from "../lib/format";
import type { SearchResponse } from "../lib/types";

export function Results({ result }: { result: SearchResponse }) {
  if (result.recommendations.length === 0) {
    return null;
  }

  return (
    <section aria-live="polite">
      {result.explanations_available ? null : <p className="notice">{FALLBACK_NOTICE}</p>}
      <ol className="cards">
        {result.recommendations.map((card, index) => (
          <li className="card" key={card.id}>
            <span className="rank">{index + 1}</span>
            <strong className="name">{card.name}</strong>
            <p className="cuisines">{card.cuisines.join(", ")}</p>
            <p className="facts">
              {formatRating(card.rating)} ★ · ₹{card.cost_for_two} for two
            </p>
            {result.explanations_available && card.explanation ? (
              <p className="ai">
                <span>AI </span>
                {card.explanation}
              </p>
            ) : (
              <p className="ai no-explanation">{NO_EXPLANATION}</p>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
