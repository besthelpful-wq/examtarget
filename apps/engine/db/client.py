import logging
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

_LOG = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase():  # type: ignore[return]
    """
    Return a Supabase client, or None when SUPABASE_URL / SUPABASE_SERVICE_KEY
    are not set (local dev without Supabase — cache is silently skipped).
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        _LOG.warning(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY not set — running without cache"
        )
        return None
    from supabase import create_client
    return create_client(url, key)
