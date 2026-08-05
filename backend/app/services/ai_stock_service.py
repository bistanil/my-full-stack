import json
import os
from google import genai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


# 1. Automatic Retries (Wait 5s, 10s, 20s... before retrying up to 3 times)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def call_gemini_with_backoff(client, prompt: str):
  return client.models.generate_content(
      model="gemini-2.0-flash",
      contents=prompt,
      config={"response_mime_type": "application/json"},
  )


def generate_ai_stock_analysis(parsed_data: dict) -> dict:
  client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

  prompt = f"""
    You are an expert equity analyst. Analyze these stock metrics:
    Company: {parsed_data.get('company_name')}
    Current Price: ₹{parsed_data.get('current_price')}
    Market Cap: ₹{parsed_data.get('market_cap')} Cr.
    Historical Sales: {json.dumps(parsed_data.get('historical_sales'))}
    Historical Net Profits: {json.dumps(parsed_data.get('historical_profits'))}

    Provide output in valid JSON:
    1. "is_good_for_investment": boolean
    2. "investment_verdict": string
    3. "best_buy_price_range": string
    4. "pros": list of strings
    5. "cons_and_risks": list of strings
    6. "detailed_analysis": string
    """

  try:
    response = call_gemini_with_backoff(client, prompt)
    return json.loads(response.text)
  except Exception as e:
    # 2. Graceful Fallback if quota remains exhausted after 3 attempts
    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
      return {
          "is_good_for_investment": False,
          "investment_verdict": "RATE LIMIT REACHED",
          "best_buy_price_range": "N/A",
          "pros": ["Screener metrics parsed successfully."],
          "cons_and_risks": [
              "Gemini API rate limit reached. Please wait ~1 minute and retry."
          ],
          "detailed_analysis": (
              "The Excel file parsed successfully, but AI insights could not be generated "
              "due to API rate limits on the Free Tier."
          ),
      }
    raise e