# user_management.py - User management with email whitelist
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from constants import USER_ROLES
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from supabase import create_client

class UserManagement:
    """User and email whitelist management"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    # ========== EMAIL WHITELIST MANAGEMENT ==========
    
    def validate_sadhguru_domain(self, email: str) -> tuple:
        """Validate if email belongs to sadhguru.org domain"""
        if not email or "@" not in email:
            return False, "Invalid email format"
        
        email_lower = email.lower().strip()
        
        if not email_lower.endswith("@sadhguru.org"):
            return False, "Only @sadhguru.org emails are allowed"
        
        return True, "Valid domain"
    
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
    
    def add_email_to_whitelist(self, email: str, added_by: str, department: str = None) -> tuple:
        """Add email to whitelist with department"""
        try:
            email_lower = email.lower().strip()
            
            # Validate domain first
            is_valid, domain_message = self.validate_sadhguru_domain(email_lower)
            if not is_valid:
                return False, domain_message
            
            # Check if email already exists (active or inactive)
            existing = self.supabase.table("email_whitelist")\
                .select("*")\
                .eq("email", email_lower)\
                .execute()
            
            if existing.data:
                # Email exists - check if it's inactive
                if not existing.data[0].get('is_active', True):
                    # Reactivate it
                    update_data = {"is_active": True, "added_by": added_by}
                    if department:
                        update_data["department"] = department
                    
                    result = self.supabase.table("email_whitelist")\
                        .update(update_data)\
                        .eq("email", email_lower)\
                        .execute()
                    print(f"✅ Reactivated {email_lower}")
                    return bool(result.data), f"Successfully reactivated {email_lower}"
                else:
                    # Already active
                    print(f"⚠️ Email {email_lower} already in whitelist")
                    return False, f"Email {email_lower} is already in the whitelist"
            
            # New email - insert it
            email_data = {
                "email": email_lower,
                "added_by": added_by,
                "is_active": True
            }
            
            if department:
                email_data["department"] = department
            
            result = self.supabase.table("email_whitelist")\
                .insert(email_data)\
                .execute()
            
            print(f"✅ Added {email_lower} to whitelist")
            return bool(result.data), f"Successfully added {email_lower} to whitelist"
        except Exception as e:
            error_msg = f"Error adding email to whitelist: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
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
        """Get all users with fresh data"""
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
        """Get users formatted for table display by role - always fresh data"""
        try:
            users = self.get_all_users()  # Always get fresh data
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
    
    def demote_spoc_to_user(self, spoc_email: str, reassign_to_spoc: str = None) -> bool:
        """Demote a SPOC back to regular user, optionally reassigning users to another SPOC"""
        try:
            # Get assigned users
            assigned_users = self.get_spoc_assignments(spoc_email)
            
            # If there are assigned users and a reassignment SPOC is provided
            if assigned_users and reassign_to_spoc:
                # Reassign all users to the new SPOC
                for user_email in assigned_users:
                    self.add_spoc_assignment(reassign_to_spoc, user_email)
            
            # Remove all old SPOC assignments
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
        """Get users that can be assigned to SPOCs (from whitelist, excluding already assigned)"""
        try:
            # Get all assignments to exclude already assigned users
            assigned_result = self.supabase.table("spoc_assignments")\
                .select("assigned_user_email").execute()
            assigned_emails = {item["assigned_user_email"] for item in assigned_result.data or []}
            
            # Get all whitelisted emails
            whitelist = self.get_whitelisted_emails()
            
            # Get already registered users for name mapping
            registered_users = self.get_all_users()
            user_names = {user['email']: user['name'] for user in registered_users}
            
            # Build assignable users list
            assignable_users = []
            for email_record in whitelist:
                email = email_record['email']
                # Skip admin emails and already assigned users
                if (email not in assigned_emails and 
                    email not in ['swapnil.padhi-ext@sadhguru.org', 'abhishek.kumar2019@sadhguru.org']):
                    
                    assignable_users.append({
                        'email': email,
                        'name': user_names.get(email, email.split('@')[0].replace('.', ' ').title()),
                        'is_registered': email in user_names
                    })
            
            return assignable_users
        except Exception as e:
            print(f"Error getting assignable users: {e}")
            return []

    def get_spoc_users(self) -> List[str]:
        """Get list of SPOC users for dropdown"""
        try:
            spoc_users = [user for user in self.get_all_users() if user['role'] == 'spoc']
            return [user['email'] for user in spoc_users]
        except Exception as e:
            print(f"Error getting SPOC users: {e}")
            return []
    
    # ========== DEPARTMENT MANAGEMENT ==========
    
    def get_departments(self) -> List[str]:
        """Get all unique departments from whitelist"""
        try:
            result = self.supabase.table("email_whitelist")\
                .select("department")\
                .eq("is_active", True)\
                .execute()
            
            departments = set()
            if result.data:
                for item in result.data:
                    dept = item.get('department')
                    if dept and dept.strip():
                        departments.add(dept.strip())
            
            return sorted(list(departments))
        except Exception as e:
            print(f"Error getting departments: {e}")
            return []

# Global user management instance
user_management = UserManagement()