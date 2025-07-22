# src/draft.py
import json
import os
import datetime
import time
import google.generativeai as genai
from openai import OpenAI

# --- Configuratie ---
LANGS = {"nl": "Nederlands", "en": "English"}
PROMPT_TPL_PATH = "prompts/step3.txt"
CURATED_DATA_PATH = "curated.json"
OUTPUT_DIR = "content"
AI_PROVIDER = os.getenv('AI_PROVIDER', 'google')

# --- Model Initialisatie (Dynamisch) ---
model = None
print(f"Gekozen AI Provider: {AI_PROVIDER}")

if AI_PROVIDER == 'google':
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable not set for Google provider.")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
elif AI_PROVIDER == 'openrouter':
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set for OpenRouter provider.")
    openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    class OpenRouterModel:
        def generate_content(self, prompt):
            response = openrouter_client.chat.completions.create(
                model="kimi-ml/kimi-2-128k",
                messages=[{"role": "user", "content": prompt}],
            )
            return type('obj', (object,), {'text': response.choices.message.content})()
    model = OpenRouterModel()
else:
    raise ValueError(f"Ongeldige AI_PROVIDER: {AI_PROVIDER}. Kies 'google' of 'openrouter'.")

# --- Hoofdlogica (ongewijzigd) ---
with open(PROMPT_TPL_PATH, "r", encoding="utf-8") as f:
    PROMPT_TPL = f.read()

try:
    with open(CURATED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"❌ Fout bij laden {CURATED_DATA_PATH}. Fout: {e}")
    exit(1)

today = datetime.date.today()
today_iso = today.isoformat()
os.makedirs(OUTPUT_DIR, exist_ok=True)

for code, lang in LANGS.items():
    edition_word = "Editie" if lang == "Nederlands" else "Edition"
    edition_date = today.strftime('%d %b %Y')

    prompt = PROMPT_TPL.replace('{json_data}', json.dumps(data, indent=2, ensure_ascii=False))
    prompt = prompt.replace('{lang}', lang)
    prompt = prompt.replace('{edition_word}', edition_word)
    prompt = prompt.replace('{edition_date}', edition_date)

    print(f"🤖 Model wordt aangeroepen voor de {lang} nieuwsbrief...")
    try:
        response = model.generate_content(prompt)
        md = response.text
        if md.strip().startswith("```markdown"):
            md = md.strip()[10:-3].strip()
        elif md.strip().startswith("```"):
             md = md.strip()[3:-3].strip()

        output_filename = f"{OUTPUT_DIR}/{today_iso}_{code}.md"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ {output_filename} geschreven")
    except Exception as e:
        print(f"❌ Fout bij API aanroep voor {lang}: {e}")

    if code != list(LANGS.keys())[-1]:
        time.sleep(10)