# Problem Statement: AI-Powered Restaurant Recommendations

People choosing where to eat often start with a long list of restaurants and still struggle to pick one that fits where they are, what they want to eat, what they can spend, and how highly a place is rated. Filters narrow the list, but they do not explain which options are the best match or why.

This project builds a restaurant recommendation service, inspired by Zomato, that combines a real restaurant dataset with a large language model. The service filters restaurants against the user’s preferences, then uses the model to rank the remaining options and explain each suggestion in plain language.

## Goal

Help a user go from a few preferences to a short, trustworthy shortlist of restaurants, with a clear reason for each recommendation.

## What the user provides

- **Location** — for example, Delhi or Bangalore
- **Budget** — low, medium, or high
- **Cuisine** — for example, Italian or Chinese
- **Minimum rating**
- **Other preferences** — optional notes such as family-friendly or quick service

## How the system works

1. **Load the data.** Ingest and clean the Zomato restaurant dataset from Hugging Face: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation). Keep the fields needed for matching and display, including restaurant name, location, cuisine, cost, and rating.
2. **Collect preferences.** Take the inputs above from the user.
3. **Filter first.** Select only restaurants that fit those preferences, and prepare that structured subset for the model. The model should reason over a relevant shortlist, not the full dataset.
4. **Rank and explain.** Prompt the model to rank the filtered restaurants, explain why each one fits, and optionally summarize the choices.
5. **Show the result.** Present the top recommendations in a format that is easy to scan.

## What the user sees

Each recommendation includes:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- A short explanation of why it matches the user’s preferences

## Done when

- Recommendations respect the user’s location, budget, cuisine, and minimum rating.
- Extra preferences, when provided, influence the ranking and the explanation.
- Every suggestion is grounded in the dataset, and the explanation states why it fits.
- The result is a small set of top options, not an unfiltered dump of matching restaurants.
