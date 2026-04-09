import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


AZURE_CLIENT_ID = _require("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = _require("AZURE_CLIENT_SECRET")
AZURE_TENANT_ID = _require("AZURE_TENANT_ID")

SHAREPOINT_HOSTNAME = _require("SHAREPOINT_HOSTNAME")
SHAREPOINT_SITE_PATH = os.getenv("SHAREPOINT_SITE_PATH", "")
SHAREPOINT_FOLDER = os.getenv("SHAREPOINT_FOLDER", "")

NVIDIA_API_KEY = _require("NVIDIA_API_KEY")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_VISION_MODEL = os.getenv("NVIDIA_VISION_MODEL", "microsoft/phi-3.5-vision-instruct")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# RAG tuning
TOP_K_CHUNKS = int(os.getenv("TOP_K_CHUNKS", "5"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
