"""Project-local configuration; secrets are never logged."""
import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent
os.environ["HAYSTACK_TELEMETRY_ENABLED"] = "false"
os.environ["HAYSTACK_CONTENT_TRACING_ENABLED"] = "false"
os.environ.setdefault("HF_HOME", str(ROOT / ".cache/huggingface"))
os.environ.setdefault("DOCLING_CACHE_DIR", str(ROOT / ".cache/docling"))
load_dotenv(ROOT / ".env")
@dataclass(frozen=True)
class Config:
    api_key: str = field(repr=False)
    pinecone_key: str = field(repr=False)
    index: str
    base_url: str = ""
    model: str = "gpt-6-luna"
    embedding_model: str = "text-embedding-3-small"
    bot_token: str = field(default="", repr=False)
    allowed_users: tuple = ()
    prefix: str = "vpg07-memory"
def load_config(require_bot=False):
    required = ["OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME"]
    if require_bot:
        required += ["TELEGRAM_BOT_TOKEN", "ALLOWED_USER_IDS"]
    if any(not os.getenv(k, "").strip() for k in required):
        raise ValueError("Заполните .env: " + ", ".join(required))
    return Config(api_key=os.environ["OPENAI_API_KEY"], pinecone_key=os.environ["PINECONE_API_KEY"],
        index=os.environ["PINECONE_INDEX_NAME"], base_url=os.getenv("OPENAI_BASE_URL", ""),
        model=os.getenv("CHAT_MODEL", "gpt-6-luna"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        allowed_users=tuple(int(x.strip()) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()))
