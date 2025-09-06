# auth.py - Authentication module with dynamic URL support and role-based access
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from supabase import create_client, Client
from config import (
    SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY,
    REDIRECT_URI, COOKIE_SECRET, COOKIE_NAME, ALLOWED_DOMAIN
)
from constants import SESSION_MAX_AGE, SESSION_SALT, ADMIN_EMAILS
from datetime import datetime
import itsdangerous
import secrets

router = APIRouter(tags=["Authentication"])

# Initialize Supabase clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
admin_supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Cookie serializer
serializer = itsdangerous.URLSafeSerializer(COOKIE_SECRET, salt=SESSION_SALT)

def ensure_users_table():
    """Ensure users table exists"""
    try:
        admin_supabase.table("users").select("id").limit(1).execute()
        return True
    except Exception:
        print("Users table not accessible. Please run the database schema.")
        return False

ensure_users_table()

@router.get("/login")
def login():
    """Initiate Google OAuth login with dynamic redirect URI"""
    try:
        provider = "google"
        redirect_to = REDIRECT_URI  # This comes from environment variables now
        
        # Use the correct Supabase OAuth URL
        url = f"{SUPABASE_URL}/auth/v1/authorize?provider={provider}&redirect_to={redirect_to}"
        
        print(f"DEBUG: Initiating OAuth to: {url}")
        print(f"DEBUG: Redirect URI configured as: {redirect_to}")
        return RedirectResponse(url)
        
    except Exception as e:
        print(f"ERROR: OAuth initiation failed: {e}")
        return RedirectResponse("/")

@router.get("/auth/callback")
def auth_callback(request: Request):
    """Handle OAuth callback with improved error handling"""
    try:
        # Get query parameters
        query_params = dict(request.query_params)
        print(f"DEBUG: Callback received with params: {query_params}")
        
        # Check for errors in callback
        if "error" in query_params:
            error_desc = query_params.get("error_description", "Unknown error")
            print(f"ERROR: OAuth callback error: {error_desc}")
            
            # Return user-friendly error page
            error_html = f"""
            <!doctype html>
            <html>
              <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>Authentication Error</h2>
                <p>There was an issue with the sign-in process: {error_desc.replace('+', ' ')}</p>
                <p><a href="/" style="color: #6a0dad; text-decoration: none;">Try signing in again</a></p>
              </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=400)
    
        # Standard callback processing
        html = """
        <!doctype html>
        <html>
          <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>Processing login...</h2>
            <p>Please wait while we complete your authentication.</p>
            <script>
              (function() {
                const hash = window.location.hash.substring(1);
                const params = new URLSearchParams(hash);
                const access_token = params.get('access_token');
                
                if (!access_token) {
                  console.error('No access token found');
                  alert('Authentication failed. Please try again.');
                  window.location.href = '/';
                  return;
                }
                
                fetch('/auth/session', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  credentials: 'same-origin',
                  body: JSON.stringify({ access_token })
                }).then(res => res.json())
                  .then(data => {
                    if (data.status === 'ok') {
                      window.location.href = '/';
                    } else {
                      alert(data.message || 'Login failed. Please try again.');
                      window.location.href = '/';
                    }
                  }).catch(err => {
                    console.error('Session creation error:', err);
                    alert('Login failed. Please try again.');
                    window.location.href = '/';
                  });
              })();
            </script>
          </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except Exception as e:
        print(f"ERROR: Callback processing failed: {e}")
        return RedirectResponse("/")

@router.post("/auth/session")
async def create_session(payload: dict, response: Response):
    """Create user session from OAuth token with role detection"""
    access_token = payload.get("access_token")
    if not access_token:
        return JSONResponse({"status": "error", "message": "Missing access token"}, status_code=400)

    try:
        print(f"DEBUG: Creating session with access token")
        
        # Get user information from Supabase
        user_resp = supabase.auth.get_user(access_token)
        user = getattr(user_resp, "user", None) or user_resp
        
        if not user:
            print("ERROR: No user data received from Supabase")
            return JSONResponse({"status": "error", "message": "Invalid user data"}, status_code=400)
        
        email = getattr(user, "email", None) or user.get("email")
        user_id = getattr(user, "id", None) or user.get("id")
        
        user_metadata = getattr(user, "user_metadata", None) or user.get("user_metadata", {})
        name = (user_metadata.get("full_name") or 
                user_metadata.get("name") or 
                email.split("@")[0] if email else "User")

        if not email:
            print("ERROR: No email found in user data")
            return JSONResponse({"status": "error", "message": "No email in user profile"}, status_code=400)

        print(f"DEBUG: Processing user: {email}")

        # Domain restriction check
        if not email.lower().endswith("@" + ALLOWED_DOMAIN.lower()):
            print(f"ERROR: Domain restriction failed for {email}")
            try:
                admin_supabase.auth.admin.delete_user(user_id)
            except Exception as cleanup_error:
                print(f"WARNING: Could not cleanup unauthorized user: {cleanup_error}")
            
            return JSONResponse({
                "status": "forbidden", 
                "message": f"Only @{ALLOWED_DOMAIN} email addresses are allowed"
            }, status_code=403)

        # FIXED: Determine user role from constants and update database
        user_role = 'admin' if email.lower() in [admin.lower() for admin in ADMIN_EMAILS] else 'user'
        print(f"DEBUG: User role determined: {user_role} for {email}")

        # Store/update user in database with automatic role assignment
        try:
            user_data = {
                "id": user_id,
                "email": email,
                "name": name,
                "role": user_role,  # Always use role from constants
                "avatar_url": user_metadata.get("avatar_url", ""),
                "provider": "google",
                "last_login": datetime.utcnow().isoformat(),
                "metadata": user_metadata
            }
            
            # Check if user exists
            existing_user = admin_supabase.table("users").select("id, role").eq("id", user_id).execute()
            
            if existing_user.data:
                # FIXED: Always update role from constants (overrides database)
                admin_supabase.table("users").update({
                    "last_login": datetime.utcnow().isoformat(),
                    "name": name,
                    "role": user_role,  # Force update role from constants
                    "avatar_url": user_metadata.get("avatar_url", ""),
                    "metadata": user_metadata
                }).eq("id", user_id).execute()
                print(f"DEBUG: Updated existing user: {email} with role: {user_role} (from constants)")
            else:
                # Create new user
                admin_supabase.table("users").insert(user_data).execute()
                print(f"DEBUG: Created new user: {email} with role: {user_role}")
                
        except Exception as db_error:
            print(f"WARNING: Could not store user data: {db_error}")
            # Continue anyway - don't fail login for database issues

        # Create secure session cookie with role
        session_data = {"email": email, "user_id": user_id, "name": name, "role": user_role}
        signed_cookie = serializer.dumps(session_data)
        
        response = JSONResponse({"status": "ok", "user": session_data})
        response.set_cookie(
            key=COOKIE_NAME, 
            value=signed_cookie, 
            httponly=True, 
            samesite="lax", 
            max_age=SESSION_MAX_AGE,
            secure=False,  # Set to True in production with HTTPS
            path="/"
        )
        
        print(f"SUCCESS: Session created for {email} with role: {user_role}")
        return response

    except Exception as e:
        print(f"ERROR: Session creation failed: {e}")
        return JSONResponse({"status": "error", "message": "Authentication failed"}, status_code=500)

@router.get("/auth/session")
async def get_session(request: Request):
    """Get current user session with role"""
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return JSONResponse({"user": None})
    
    try:
        data = serializer.loads(cookie)
        return JSONResponse({
            "user": {
                "email": data.get("email"), 
                "user_id": data.get("user_id"),
                "name": data.get("name"),
                "role": data.get("role", "user")  # Default to user if role not found
            }
        })
    except Exception as e:
        print(f"WARNING: Invalid session cookie: {e}")
        return JSONResponse({"user": None})

@router.get("/logout")
def logout():
    """Logout user and clear session"""
    try:
        resp = RedirectResponse("/")
        resp.delete_cookie(COOKIE_NAME)
        print("DEBUG: User logged out successfully")
        return resp
    except Exception as e:
        print(f"ERROR: Logout failed: {e}")
        return RedirectResponse("/")

def get_logged_in_user(request: Request):
    """Helper to extract user from request with role"""
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    
    try:
        data = serializer.loads(cookie)
        return {
            "email": data.get("email"),
            "user_id": data.get("user_id"), 
            "name": data.get("name"),
            "role": data.get("role", "user")  # Default to user if role not found
        }
    except Exception as e:
        print(f"WARNING: Could not parse user session: {e}")
        return None