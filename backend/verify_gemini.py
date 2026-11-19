import sys
import re
import traceback
from app.core.config import settings
from google import genai
from google.genai import types

def sanitize_message(msg: str, secret: str) -> str:
    """Mask any accidental appearance of secret key in messages or traces."""
    if secret and secret in msg:
        msg = msg.replace(secret, "[REDACTED_API_KEY]")
    msg = re.sub(r'AIzaSy[A-Za-z0-9_-]{33}', '[REDACTED_API_KEY]', msg)
    return msg

def test_connection():
    api_key = settings.GEMINI_API_KEY.strip()
    model_name = settings.GEMINI_MODEL.strip() or "gemini-3.8-flash"

    print("=" * 60, flush=True)
    print("DataFix - Secure Gemini API Connection Test", flush=True)
    print("=" * 60, flush=True)
    print(f"LOADED_MODEL  : {model_name}", flush=True)

    if not api_key:
        print("STATUS        : FAILED", flush=True)
        print("ERROR         : GEMINI_API_KEY is not set or empty in backend/.env.", flush=True)
        return False

    print(f"KEY_STATUS    : Configured (Length: {len(api_key)}, masked)", flush=True)

    try:
        # Initialize client with a 30s timeout and single attempt to prevent long tenacity loops
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=30000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

        # Step 1: Verify API key authentication & model existence
        print("AUTH_CHECK    : Verifying API key & model metadata...", flush=True)
        model_info = client.models.get(model=model_name)
        display_name = getattr(model_info, 'display_name', model_name)
        print(f"AUTH_RESULT   : Authenticated successfully! (Model: {display_name})", flush=True)

        # Step 2: Test content generation
        print("TEST_REQUEST  : Sending prompt to Gemini...", flush=True)
        prompt = "Respond with exact words: DataFix Gemini connection successful"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        response_text = response.text.strip() if response.text else ""
        print("STATUS        : SUCCESS", flush=True)
        print(f"RESPONSE      : {response_text}", flush=True)
        return True

    except Exception as e:
        safe_err = sanitize_message(str(e), api_key)
        print("STATUS        : FAILED", flush=True)
        print(f"ERROR         : {safe_err}", flush=True)

        if "503" in safe_err or "UNAVAILABLE" in safe_err:
            print("\nDIAGNOSIS     : Google API returned 503 UNAVAILABLE (High Demand spike).", flush=True)
            print("                Your API key and connection are valid, but Google's servers for", flush=True)
            print(f"                '{model_name}' are temporarily overloaded.", flush=True)
            print("RECOMMENDATION: Either retry in a few moments, or temporarily switch GEMINI_MODEL", flush=True)
            print("                in backend/.env to 'gemini-3.1-flash-lite' or 'gemini-3.5-flash-lite'.", flush=True)
        elif "404" in safe_err or "NOT_FOUND" in safe_err:
            print("\nDIAGNOSIS     : Model ID not found or deprecated.", flush=True)
            print(f"RECOMMENDATION: Check available models or update GEMINI_MODEL in backend/.env.", flush=True)

        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
