# Google Stitch prompt

Paste the prompt below into [Google Stitch](https://stitch.withgoogle.com) to generate UI images for the Next.js frontend. The screens follow [architecture.md](architecture.md). Stitch should design the interface only. The Python API already filters, ranks, and explains.

Generate one desktop frame (1440 wide) and one mobile frame (390 wide) for each screen.

---

Design a high-fidelity UI for a Next.js App Router page called “Find a restaurant.” It is one screen, not a marketing site and not a restaurant directory. A person sets a few preferences, then sees at most five restaurants and a reason for each. The look is warm and editorial: paper background `#f6f3ee`, ink `#1c1917`, muted stone `#57534e`, cards `#fffdfb`, hairline `#e7e5e4`, and a burnt-orange accent `#9a3412` with cream text `#fff7ed`. Use a clean sans serif. Plenty of whitespace. No Zomato logo, no map, no infinite scroll, no ads, and no photographs of the named restaurants. Scan the list through type, a rating, and a cost. Do not invent extra restaurants, prices, or ratings.

**Screen 1 — Ready to search.** Desktop: a narrow column, about 640px, centered. Mobile: the same column with 16px side padding. Title “Find a restaurant.” Subtitle “Set location, budget, cuisine, and rating. Optional notes can describe what else matters.” Then a form:

- Location, a select, placeholder “Choose a neighborhood,” value Bellandur. Neighborhoods are Bangalore areas such as Banashankari and Bellandur, not cities such as Delhi.
- Budget, three pills in a row: “Low · up to ₹300”, “Medium · ₹301–₹500” selected, “High · above ₹500”. The rupee range must be visible. Budget is a band, not an exact price.
- Cuisine, a select, value North Indian.
- Minimum rating, a number field, value 4, hint “From 1.8 to 4.9 in this catalog.”
- Other preferences, an optional textarea, placeholder “Family-friendly, quick service,” empty.
- A full-width button, “Find restaurants.”

**Screen 2 — Five recommendations.** Same form, values kept, below a results panel. Heading “5 recommendations.” One summary, once, above the cards and not repeated on them: “These five restaurants best match your North Indian, medium-budget preferences in Bellandur, ordered by rating and value.” Then a numbered list of five cards. Each card shows the name, every cuisine, “Rating” plus the number, “Estimated ₹… for two,” and the explanation. Use this copy exactly:

1. eat.fit. Healthy Food, North Indian, Biryani, Continental, Desserts. Rating 4.4. Estimated ₹500 for two. Highest rating among the matches, at the medium-budget limit, and it serves North Indian dishes in Bellandur.
2. BOX8- Desi Meals. North Indian, Mughlai, Fast Food. Rating 4.2. Estimated ₹500 for two. Strong rating, medium cost, and a clear North Indian menu.
3. Shree Khana Khazana. North Indian, Chinese, Rajasthani. Rating 4.1. Estimated ₹450 for two. Meets the rating, costs less than the ₹500 options, and serves North Indian food.
4. Faasos. North Indian, Biryani, Fast Food. Rating 4.1. Estimated ₹500 for two. Meets the rating and the medium budget, with North Indian dishes.
5. Eden Huts Restaurant. Chinese, North Indian. Rating 4. Estimated ₹400 for two. Meets the minimum rating and is the lowest cost of the five.

**Screen 3 — One recommendation.** Heading “1 recommendation,” singular. Summary once: “One strong match.” A single card: Jalsa. North Indian, Chinese. Rating 4.1. Estimated ₹800 for two. Explanation: “Quick service fits this Chinese spot.” The layout must not look empty or broken because there is only one card.

**Screen 4 — No matches.** No cards and no unrelated restaurants. A calm message: “No restaurants match location Banashankari, cuisine Chinese, minimum rating 4.9, and budget high.” The form stays filled with those values so the person can change them.

**Screen 5 — No AI explanation.** Heading “4 recommendations.” A notice above the list: “These matches use catalog facts. An AI explanation was not produced.” Cards show name, all cuisines, rating, and estimated cost for two. In place of an explanation, each card says “No AI explanation was produced.” Sample cards: Ayodhya Upachar, South Indian, Rating 4.3, Estimated ₹200 for two; Udupi Ruchi Grand, South Indian, Rating 4.2, Estimated ₹200 for two.

**Screen 6 — Form errors.** Do not show recommendations. An error list above the fields: “Enter a location.” “Choose a budget: low, medium, or high.” “Enter a cuisine.” “Enter a minimum rating from 0 to 5.” Keep whatever the person already typed.

**Screen 7 — Searching.** The form is submitted and disabled. The button reads “Finding restaurants…” and the results area shows a short waiting state. Do not show a spinner that implies a long directory is loading. The wait is for a short list of five.

On desktop, the form and the results stack in one column, results first after a search. On mobile, the same order, with cards full width and budget pills wrapping. Every visible rating and cost is the figure printed above. Do not add “/5”, delivery time, photos, phone numbers, addresses, or a sixth restaurant.
