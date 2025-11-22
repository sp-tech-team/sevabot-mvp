"""
Supabase Client Factory
Centralized Supabase client creation with SSL verification handling for local development
"""

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
import urllib3

# Disable SSL warnings for local development
if not IS_PRODUCTION:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_supabase_client(use_service_role: bool = False) -> Client:
    """
    Get configured Supabase client with SSL verification handling

    Args:
        use_service_role: If True, uses service role key (admin access)
                         If False, uses anon key (regular access)

    Returns:
        Configured Supabase client
    """
    key = SUPABASE_SERVICE_ROLE_KEY if use_service_role else SUPABASE_KEY

    # Configure SSL verification based on environment
    client_options = {}
    if not IS_PRODUCTION:
        # Disable SSL verification for local development (helps with corporate proxies)
        client_options = {"verify": False}

    return create_client(SUPABASE_URL, key, options=client_options)


# Pre-configured clients for convenience
supabase_client = get_supabase_client(use_service_role=False)
supabase_admin = get_supabase_client(use_service_role=True)
