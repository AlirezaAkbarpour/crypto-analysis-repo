# Crypto Historical Analysis

Download daily CoinGecko price history and compare a token with Bitcoin using returns, volatility, correlation, lag analysis, and monthly returns.

## Model-assisted analysis

`crypto-data-agent.py` adds local analytics and can send the computed report to any OpenAI-compatible chat-completions endpoint. The model receives JSON statistics rather than raw secrets or credentials.

```bash
# Local report only; no API key required
python crypto-data-agent.py fabric-foundation-1y.csv --report crypto-report.json

# Ask a configured model a question
# Set MODEL_API_KEY in your environment; never put it in source files.
python crypto-data-agent.py fabric-foundation-1y.csv \
  --question "آیا مومنتوم کوتاه‌مدت در حال بهبود است؟"
```

Optional environment variables:

- `MODEL_API_KEY`: model provider key
- `MODEL_BASE_URL`: OpenAI-compatible base URL; defaults to `https://api.openai.com/v1`
- `MODEL_NAME`: model name; defaults to `gpt-4o-mini`

The analysis prompt is in `prompts/crypto-analysis-prompt.md`. It requires uncertainty, avoids unsupported claims, and does not provide financial advice.

## Original script

```bash
python scripts/crypto-historical-analysis.py <coin_id> <days> <output.csv>
```

Example:

```bash
python scripts/crypto-historical-analysis.py robo-token-2 730 fabric-prices.csv
```
