# Canteen Menu Planner

Automated weekly menu planning using Gemini models made in Python.

>Gemini API key is needed from google: [https://aistudio.google.com/app/api-keys](https://aistudio.google.com/app/api-keys)

## Setup & Run

1.  **Python 3.12+**
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set your `GEMINI_API_KEY` in a `.env` file.

4.  Run with:
    ```bash
    uvicorn main:app --reload
    ```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
