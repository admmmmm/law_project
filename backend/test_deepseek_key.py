from pathlib import Path
import os

from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path, override=True)

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("HIPPORAG_LLM_BASE_URL", "https://api.deepseek.com"),
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("HIPPORAG_LLM_NAME", "deepseek-chat"),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        print("AUTH_OK")
        print(response.choices[0].message.content)
    except Exception as exc:
        print("AUTH_FAIL")
        print(f"{exc.__class__.__name__}: {exc}")


if __name__ == "__main__":
    main()
