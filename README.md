# HEYRA: Canteen Menu Planner

Automated weekly menu planning using Gemini thinking models. This application helps canteen chefs plan a 5-day menu with two tracks (Meat and Vegetarian) while respecting dietary restrictions and cost constraints.

## Features

- **Gemini Thinking Models**: Uses advanced reasoning to select compatible ingredients and design balanced meals.
- **Live Reasoning Stream**: Watch the AI "think" through the planning process in real-time.
- **Dietary Filters**: Exclude allergens (Gluten, Nuts, Dairy) dynamically.
- **Graceful Failure**: Clear reporting when constraints are unsatisfiable or the AI produces invalid plans.
- **Cost & Nutrition Summary**: Automatic calculation of weekly costs and allergen tracking.

## Setup

1.  **Python 3.12+**
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set your `GEMINI_API_KEY` in a `.env` file (copied from `.env.example` if available).

## Run

```bash
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
