import os
from functools import lru_cache
from typing import Optional

from supabase import create_client, Client


def _is_configured() -> bool:
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    return bool(url and key)


@lru_cache
def get_supabase() -> Optional[Client]:
    """Returns Supabase client or None if not configured."""
    if not _is_configured():
        return None
    url = os.getenv("SUPABASE_URL", "")
    if url and not url.startswith("http"):
        url = f"https://{url}"
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    return create_client(url, key)
