"""Preference form. Submissions are validated by Phase 2 before any filter runs."""

import json
from collections.abc import Sequence
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from app.config import NOTES_MAX_LENGTH, UI_HOST, UI_PORT
from app.errors import InvalidPreference
from app.models import Budget, Preferences, Restaurant
from phase1.store import Catalog
from phase2.collect import accept_json, collect, preference_errors
from phase2.options import PreferenceOptions, options_for
from phase3 import filter_candidates
from phase4 import RankResult, rank
from phase4.rank import ChatClient
from phase5 import render_results, results_payload

_FIELDS = ("location", "budget", "cuisine", "min_rating", "notes")


def parse_preferences(form: dict[str, str]) -> Preferences:
    """Build one Preference object from form fields."""
    notes = form.get("notes", "")
    return Preferences(
        location=form.get("location", ""),
        budget=form.get("budget", ""),
        cuisine=form.get("cuisine", ""),
        min_rating=form.get("min_rating", ""),
        notes=notes or None,
    )


def render_page(
    form: dict[str, str] | None = None,
    preferences: Preferences | None = None,
    errors: list[str] | None = None,
    options: PreferenceOptions | None = None,
    ranked: RankResult | None = None,
    known: Sequence[Restaurant] | None = None,
) -> str:
    values = {field: "" for field in _FIELDS}
    if form:
        values.update({field: form.get(field, "") for field in _FIELDS})
    if preferences is not None:
        values["location"] = preferences.location
        values["budget"] = preferences.budget.value
        values["cuisine"] = preferences.cuisine
        values["min_rating"] = f"{preferences.min_rating:g}"
        values["notes"] = preferences.notes or ""

    error_html = ""
    if errors:
        items = "".join(f"<li>{escape(message)}</li>" for message in errors)
        error_html = f'<ul class="errors" role="alert">{items}</ul>'

    accepted_html = ""
    if preferences is not None:
        notes = preferences.notes or "None"
        accepted_html = f"""
        <section class="accepted" aria-live="polite">
          <h2>Preferences accepted</h2>
          <dl>
            <div><dt>Location</dt><dd>{escape(preferences.location)}</dd></div>
            <div><dt>Budget</dt><dd>{escape(preferences.budget.value)}</dd></div>
            <div><dt>Cuisine</dt><dd>{escape(preferences.cuisine)}</dd></div>
            <div><dt>Minimum rating</dt><dd>{preferences.min_rating:g}</dd></div>
            <div><dt>Other preferences</dt><dd>{escape(notes)}</dd></div>
          </dl>
          <p>These preferences were checked against the catalog.</p>
        </section>
        """

    candidates_html = render_results(ranked, known) if ranked is not None else ""

    budget_inputs = []
    for band in Budget:
        checked = " checked" if values["budget"] == band.value else ""
        budget_inputs.append(
            f'<label class="choice"><input type="radio" name="budget" value="{band.value}"{checked} required> {band.value}</label>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Restaurant preferences</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1c1917;
      --muted: #57534e;
      --line: #e7e5e4;
      --paper: #f6f3ee;
      --card: #fffdfb;
      --accent: #9a3412;
      --accent-ink: #fff7ed;
      --error: #9f1239;
      --ok: #14532d;
      --ok-bg: #f0fdf4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--paper);
      color: var(--ink);
      font: 16px/1.5 "Segoe UI", sans-serif;
    }}
    main {{
      width: min(40rem, calc(100% - 2rem));
      margin: 2.5rem auto;
    }}
    h1 {{
      margin: 0 0 0.35rem;
      font-size: 1.75rem;
      letter-spacing: -0.02em;
    }}
    .lede {{
      margin: 0 0 1.25rem;
      color: var(--muted);
    }}
    form, .accepted, .results {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 1.25rem;
    }}
    .accepted, .results {{
      margin-bottom: 1rem;
    }}
    .accepted {{
      background: var(--ok-bg);
      border-color: #bbf7d0;
    }}
    .accepted h2, .results h2 {{
      margin: 0 0 0.75rem;
      color: var(--ok);
      font-size: 1.05rem;
    }}
    .summary {{ margin: 0 0 0.75rem; }}
    .results ol {{ margin: 0; padding-left: 1.2rem; }}
    .results li {{ margin: 0.8rem 0; }}
    .meta {{ color: var(--muted); margin: 0.15rem 0; }}
    .why {{ margin: 0.35rem 0 0; }}
    .no-explanation {{ color: var(--muted); font-style: italic; }}
    dl {{ margin: 0; }}
    dl div {{
      display: grid;
      grid-template-columns: 9.5rem 1fr;
      gap: 0.5rem;
      padding: 0.35rem 0;
      border-top: 1px solid #dcfce7;
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; }}
    label, legend {{
      display: block;
      font-weight: 600;
      margin-bottom: 0.35rem;
    }}
    .field {{ margin-bottom: 1rem; }}
    .hint {{
      display: block;
      margin-top: 0.3rem;
      color: var(--muted);
      font-size: 0.875rem;
    }}
    input[type="number"], select, textarea {{
      width: 100%;
      padding: 0.65rem 0.75rem;
      border: 1px solid var(--line);
      border-radius: 8px;
      font: inherit;
      color: inherit;
      background: white;
    }}
    textarea {{ min-height: 6rem; resize: vertical; }}
    fieldset {{
      margin: 0 0 1rem;
      padding: 0;
      border: 0;
    }}
    .choices {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
    .choice {{
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.55rem 0.75rem;
      border: 1px solid var(--line);
      border-radius: 999px;
      font-weight: 500;
      text-transform: capitalize;
    }}
    button {{
      width: 100%;
      margin-top: 0.25rem;
      padding: 0.75rem 1rem;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: var(--accent-ink);
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }}
    .errors {{
      margin: 0 0 1rem;
      padding: 0.75rem 0.75rem 0.75rem 1.5rem;
      border-radius: 8px;
      background: #fff1f2;
      color: var(--error);
    }}
  </style>
</head>
<body>
  <main>
    <h1>Find a restaurant</h1>
    <p class="lede">Set location, budget, cuisine, and rating. Optional notes can describe what else matters.</p>
    {accepted_html}
    {candidates_html}
    {_form_html(values, error_html, budget_inputs, options)}
  </main>
</body>
</html>
"""


def _select(name: str, selected: str, choices: tuple[str, ...], placeholder: str) -> str:
    options = [f'<option value="">{escape(placeholder)}</option>']
    for choice in choices:
        mark = " selected" if choice == selected else ""
        options.append(f'<option value="{escape(choice)}"{mark}>{escape(choice)}</option>')
    return f'<select id="{name}" name="{name}" required>{"".join(options)}</select>'


def _form_html(
    values: dict[str, str],
    error_html: str,
    budget_inputs: list[str],
    options: PreferenceOptions | None,
) -> str:
    if options is None:
        return "<p>Build the catalog with <code>python -m phase1</code> before choosing preferences.</p>"
    return f"""
    <form method="post" action="/">
      {error_html}
      <div class="field">
        <label for="location">Location</label>
        {_select("location", values["location"], options.locations, "Choose a neighborhood")}
      </div>
      <fieldset>
        <legend>Budget</legend>
        <div class="choices">{"".join(budget_inputs)}</div>
      </fieldset>
      <div class="field">
        <label for="cuisine">Cuisine</label>
        {_select("cuisine", values["cuisine"], options.cuisines, "Choose a cuisine")}
      </div>
      <div class="field">
        <label for="min_rating">Minimum rating</label>
        <input id="min_rating" name="min_rating" type="number" required min="{options.rating_min}" max="{options.rating_max}" step="0.1" value="{escape(values["min_rating"])}">
        <span class="hint">From {options.rating_min:g} to {options.rating_max:g} in this catalog.</span>
      </div>
      <div class="field">
        <label for="notes">Other preferences</label>
        <textarea id="notes" name="notes" maxlength="{NOTES_MAX_LENGTH}" placeholder="Family-friendly, quick service">{escape(values["notes"])}</textarea>
        <span class="hint">Optional. Up to {NOTES_MAX_LENGTH} characters.</span>
      </div>
      <button type="submit">Save preferences</button>
    </form>
    """


def handle_form(
    form: dict[str, str],
    catalog: Catalog | None,
    client: ChatClient | None = None,
) -> str:
    options = options_for(catalog) if catalog is not None else None
    if catalog is None:
        return render_page(
            form=form,
            errors=["Build the catalog before submitting preferences."],
            options=None,
        )
    try:
        preferences = collect(form, catalog)
    except InvalidPreference as error:
        return render_page(form=form, errors=error.errors, options=options)
    filtered = filter_candidates(preferences, catalog)
    return render_page(
        form=form,
        preferences=preferences,
        options=options,
        ranked=rank(filtered, client=client),
        known=filtered.candidates,
    )


class PreferenceHandler(BaseHTTPRequestHandler):
    catalog: Catalog | None = None
    rank_client: ChatClient | None = None

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/preferences":
            payload = self._options_payload()
            self._send_json(payload, 400 if "errors" in payload else 200)
            return
        if path != "/":
            self.send_error(404)
            return
        options = options_for(self.catalog) if self.catalog is not None else None
        self._send(render_page(options=options))

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        if path == "/preferences":
            if self.catalog is None:
                self._send_json({"errors": ["Build the catalog before submitting preferences."]}, 400)
                return
            status, payload = accept_json(raw, self.catalog)
            if status == 200:
                preferences = Preferences.model_validate(payload)
                filtered = filter_candidates(preferences, self.catalog)
                ranked = rank(filtered, client=self.rank_client)
                payload = {**payload, **results_payload(ranked, known=filtered.candidates)}
            self._send_json(payload, status)
            return
        if path != "/":
            self.send_error(404)
            return
        parsed = parse_qs(raw, keep_blank_values=True)
        form = {key: values[0] if values else "" for key, values in parsed.items()}
        self._send(handle_form(form, self.catalog, client=self.rank_client))

    def _options_payload(self) -> dict[str, object]:
        if self.catalog is None:
            return {"errors": ["Build the catalog before submitting preferences."]}
        options = options_for(self.catalog)
        return {
            "locations": list(options.locations),
            "cuisines": list(options.cuisines),
            "rating_min": options.rating_min,
            "rating_max": options.rating_max,
            "budgets": list(options.budgets),
        }

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send(self, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(
    catalog: Catalog | None = None,
    host: str = UI_HOST,
    port: int = UI_PORT,
) -> None:
    PreferenceHandler.catalog = catalog
    server = ThreadingHTTPServer((host, port), PreferenceHandler)
    print(f"Preference form at http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
