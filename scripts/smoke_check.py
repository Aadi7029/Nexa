import os
import sys
import asyncio
import traceback

# Ensure repo root is on sys.path and set cwd so `import app` works
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.core.config import settings

def main():
    print('cwd:', os.getcwd())
    print('settings.openai_model =', repr(settings.openai_model))
    print('OPENAI_API_KEY present =', bool(settings.openai_api_key))

    if not settings.openai_api_key:
        print('\nNo OpenAI API key found in settings. Skipping live AI request.')
        return

    try:
        from app.services.ai_service import generate_reply_suggestions

        ctx = {'text': 'Hello — provide three short reply suggestions.', 'sender_name': 'SmokeTest'}
        print('\nCalling generate_reply_suggestions(...) (this makes a real HTTP request)')
        result = asyncio.run(generate_reply_suggestions(ctx))
        print('\nResult from AI service:', result)
    except Exception:
        print('\nException during AI call:')
        traceback.print_exc()


if __name__ == '__main__':
    main()