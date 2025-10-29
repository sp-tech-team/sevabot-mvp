# user_management.py - User management with email whitelist
from typing import List, Dict, Optional
from datetime import datetime
from constants import USER_ROLES
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from supabase import create_client

class UserManagement:
    """User and email whitelist management"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    # ========== EMAIL WHITELIST MANAGEMENT ==========
    
    def get_whitelisted_emails(self) -> List[Dict]:
        """Get all whitelisted emails"""
        try:
            result = self.supabase.table("email_whitelist")\
                .select("*")\
                .eq("is_active", True)\
                .order("added_at", desc=True)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting whitelisted emails: {e}")
            return []
    
    def add_email_to_whitelist(self, email: str, added_by: str) -> bool:
        """Add email to whitelist"""
        try:
            email_lower = email.lower()
            
            # Check if email already exists (active or inactive)
            existing = self.supabase.table("email_whitelist")\
                .select("*")\
                .eq("email", email_lower)\
                .execute()
            
            if existing.data:
                # Email exists - check if it's inactive
                if not existing.data[0].get('is_active', True):
                    # Reactivate it
                    result = self.supabase.table("email_whitelist")\
                        .update({"is_active": True, "added_by": added_by})\
                        .eq("email", email_lower)\
                        .execute()
                    print(f"✅ Reactivated {email_lower}")
                    return bool(result.data)
                else:
                    # Already active
                    print(f"⚠️ Email {email_lower} already in whitelist")
                    return False
            
            # New email - insert it
            email_data = {
                "email": email_lower,
                "added_by": added_by,
                "is_active": True
            }
            
            result = self.supabase.table("email_whitelist")\
                .insert(email_data)\
                .execute()
            
            print(f"✅ Added {email_lower} to whitelist")
            return bool(result.data)
        except Exception as e:
            print(f"❌ Error adding email to whitelist: {e}")
            return False
    
    def remove_email_from_whitelist(self, email: str) -> bool:
        """Remove email from whitelist"""
        try:
            result = self.supabase.table("email_whitelist")\
                .update({"is_active": False})\
                .eq("email", email.lower())\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error removing email from whitelist: {e}")
            return False
    
    def is_email_whitelisted(self, email: str) -> bool:
        """Check if email is whitelisted"""
        try:
            result = self.supabase.table("email_whitelist")\
                .select("id")\
                .eq("email", email.lower())\
                .eq("is_active", True)\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error checking email whitelist: {e}")
            return False
    
    # ========== USER MANAGEMENT ==========
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        try:
            result = self.supabase.table("users")\
                .select("email, name, role, last_login, created_at")\
                .order("created_at", desc=True)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    def get_users_by_role(self, role: str) -> List[List[str]]:
        """Get users formatted for table display by role"""
        try:
            users = self.get_all_users()
            filtered_users = [user for user in users if user['role'] == role]
            
            # Format for table: [Name, Email, Last Login, Date Added]
            table_data = []
            for user in filtered_users:
                table_data.append([
                    user.get('name', 'Unknown'),
                    user['email'],
                    user.get('last_login', 'Never')[:10] if user.get('last_login') else 'Never',
                    user.get('created_at', 'Unknown')[:10] if user.get('created_at') else 'Unknown'
                ])
            
            return table_data
        except Exception as e:
            print(f"Error getting users by role: {e}")
            return []
    
    def promote_user_to_spoc(self, user_email: str) -> bool:
        """Promote a user to SPOC role"""
        try:
            result = self.supabase.table("users")\
                .update({"role": "spoc"})\
                .eq("email", user_email)\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error promoting user to SPOC: {e}")
            return False
    
    def demote_spoc_to_user(self, spoc_email: str) -> bool:
        """Demote a SPOC back to regular user"""
        try:
            # Remove all SPOC assignments first
            self.supabase.table("spoc_assignments")\
                .delete()\
                .eq("spoc_email", spoc_email)\
                .execute()
            
            # Update role to user
            result = self.supabase.table("users")\
                .update({"role": "user"})\
                .eq("email", spoc_email)\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error demoting SPOC to user: {e}")
            return False
    
    # ========== SPOC ASSIGNMENTS ==========
    
    def add_spoc_assignment(self, spoc_email: str, user_email: str) -> bool:
        """Add user assignment to SPOC"""
        try:
            # Check if assignment already exists
            existing = self.supabase.table("spoc_assignments")\
                .select("id")\
                .eq("spoc_email", spoc_email)\
                .eq("assigned_user_email", user_email)\
                .execute()
            
            if existing.data:
                print(f"Assignment already exists: {spoc_email} -> {user_email}")
                return False
            
            assignment_data = {
                "spoc_email": spoc_email,
                "assigned_user_email": user_email
            }
            
            result = self.supabase.table("spoc_assignments")\
                .insert(assignment_data)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error adding SPOC assignment: {e}")
            return False
    
    def remove_spoc_assignment(self, spoc_email: str, user_email: str) -> bool:
        """Remove user assignment from SPOC"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .delete()\
                .eq("spoc_email", spoc_email)\
                .eq("assigned_user_email", user_email)\
                .execute()
            
            return True
        except Exception as e:
            print(f"Error removing SPOC assignment: {e}")
            return False
    
    def get_spoc_assignments(self, spoc_email: str) -> List[str]:
        """Get list of users assigned to a SPOC"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .select("assigned_user_email")\
                .eq("spoc_email", spoc_email)\
                .execute()
            
            if result.data:
                return [item["assigned_user_email"] for item in result.data]
            return []
        except Exception as e:
            print(f"Error getting SPOC assignments: {e}")
            return []
    
    def get_all_spoc_assignments(self) -> Dict[str, List[str]]:
        """Get all SPOC assignments"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .select("*")\
                .execute()
            
            assignments = {}
            if result.data:
                for item in result.data:
                    spoc_email = item["spoc_email"]
                    user_email = item["assigned_user_email"]
                    
                    if spoc_email not in assignments:
                        assignments[spoc_email] = []
                    assignments[spoc_email].append(user_email)
            
            return assignments
        except Exception as e:
            print(f"Error getting all SPOC assignments: {e}")
            return {}
    
    def get_assignments_overview_table(self) -> List[List[str]]:
        """Get assignments formatted for overview table"""
        try:
            assignments_result = self.supabase.table("spoc_assignments")\
                .select("*")\
                .order("created_at", desc=True)\
                .execute()
            
            if not assignments_result.data:
                return []
            
            # Get user details for names
            users = self.get_all_users()
            user_details = {user['email']: user['name'] for user in users}
            
            # Build assignments table
            assignments_data = []
            for assignment in assignments_result.data:
                spoc_email = assignment["spoc_email"]
                user_email = assignment["assigned_user_email"]
                created_date = assignment["created_at"][:10]
                
                assignments_data.append([
                    spoc_email,
                    user_details.get(spoc_email, "Unknown"),
                    user_email,
                    user_details.get(user_email, "Unknown"),
                    created_date
                ])
            
            return assignments_data
        except Exception as e:
            print(f"Error loading assignments overview: {e}")
            return []
    
    def get_assignable_users_for_spoc(self) -> List[Dict]:
        """Get users that can be assigned to SPOCs (from whitelist, not just registered users)"""
        try:
            # Get all whitelisted emails
            whitelist = self.get_whitelisted_emails()
            
            # Get already registered users for name mapping
            registered_users = self.get_all_users()
            user_names = {user['email']: user['name'] for user in registered_users}
            
            # Build assignable users list
            assignable_users = []
            for email_record in whitelist:
                email = email_record['email']
                # Skip admin emails
                if email in ['swapnil.padhi-ext@sadhguru.org', 'abhishek.kumar2019@sadhguru.org']:
                    continue
                
                assignable_users.append({
                    'email': email,
                    'name': user_names.get(email, email.split('@')[0].replace('.', ' ').title()),
                    'is_registered': email in user_names
                })
            
            return assignable_users
        except Exception as e:
            print(f"Error getting assignable users: {e}")
            return []

# Global user management instance
user_management = UserManagement()