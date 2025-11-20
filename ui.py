from fastapi import Request, FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
import gradio as gr
from gradio.routes import mount_gradio_app

from auth import get_logged_in_user
from ui_service import ui_service
from user_management import user_management
from file_services import enhanced_file_service
from chat_service import chat_service
from constants import USER_ROLES

from ui_styles import (get_favicon_link, get_isha_logo_svg, get_landing_page_html, get_main_app_css)

def create_landing_page_html() -> str:
    """Landing page HTML"""
    return get_landing_page_html()


def create_gradio_interface():
    """Create main Gradio interface with enhanced file management"""
    
    with gr.Blocks(
        theme=gr.themes.Soft(), 
        title="Isha Sevabot",
        head=get_favicon_link(),
        css=get_main_app_css()
    ) as demo:
        
        # State variables
        current_conversation_id = gr.State(None)
        last_assistant_message_id = gr.State(None)
        selected_user_for_file_manager = gr.State(None)
        selected_chat_user = gr.State(None)
        pending_feedback = gr.State(False)  # Track if feedback is pending
        pending_feedback_message_id = gr.State(None)  # Track which message needs feedback

        # Header with user greeting
        with gr.Row():
            with gr.Column(scale=3):
                sevabot_logo = gr.HTML(get_isha_logo_svg(), elem_classes="sevabot-logo")

            with gr.Column(scale=1):
                with gr.Row():
                    namaskaram_user = gr.Button("", variant="secondary", interactive=False, scale=4)
                    logout_btn = gr.Button("Logout", variant="stop", elem_classes="logout-btn", scale=1)
        
        # Main tabs
        with gr.Tabs():
            # Chat Tab
            with gr.TabItem("💬 Chat"):
                with gr.Row():
                    # Left sidebar - Sessions
                    with gr.Column(scale=1, min_width=250):
                        gr.Markdown("### Chat Sessions")
                        with gr.Row():
                            with gr.Row():
                                new_chat_btn = gr.Button("➕", variant="primary", min_width=60, elem_classes="new-chat-btn")
                                delete_chat_btn = gr.Button("🗑️", variant="secondary", min_width=60, elem_classes="delete-chat-btn")
                                refresh_chat_btn = gr.Button("🔄", variant="secondary", min_width=60, elem_classes="refresh-chat-btn")
                        sessions_radio = gr.Radio(label="Conversations", choices=[], value=None, interactive=True, show_label=False)
                        
                    # Main content area
                    with gr.Column(scale=4):
                        # Admin/SPOC user selection for chat viewing
                        with gr.Column(visible=False) as admin_chat_user_section:
                            gr.Markdown("#### Admin/SPOC: View User Chats")
                            
                            with gr.Row():
                                chat_users_dropdown = gr.Dropdown(
                                    label="Select User to View Chats",
                                    choices=[],
                                    value=None,
                                    interactive=True,
                                    filterable=True,
                                    allow_custom_value=True,
                                    scale=3
                                )
                                refresh_chat_users_btn = gr.Button("🔄 Refresh Users", variant="secondary", scale=1)
                        
                        # Chat interface
                        chatbot = gr.Chatbot(
                            label="",
                            height="70vh",
                            show_copy_button=True,
                            show_share_button=False,
                            type="messages"
                        )
                        
                        # Feedback row
                        with gr.Column(visible=False, elem_classes="feedback-container") as feedback_row:
                            gr.Markdown("**Rate how well the query is answered:**")
                            
                            with gr.Row():
                                # Radio buttons for feedback selection
                                feedback_radio = gr.Radio(
                                    choices=["✅ Fully", "⚠️ Partially", "❌ Nopes"],
                                    value=None,
                                    label="",
                                    interactive=True,
                                    elem_classes="feedback-radio-inline"
                                )
                            
                            # Feedback remarks and submit in same row
                            with gr.Row():
                                feedback_remarks = gr.Textbox(
                                    label="Additional feedback (required for Partially/Nopes)",
                                    placeholder="Please explain what was missing or incorrect...",
                                    lines=2,
                                    scale=8,
                                    elem_classes="feedback-remarks"
                                )
                                
                                submit_feedback_btn = gr.Button(
                                    "Submit Feedback",
                                    variant="primary", 
                                    scale=1,
                                    elem_classes="feedback-submit-btn"
                                )
                        
                        # Message input
                        with gr.Row():
                            with gr.Column(scale=10):
                                chat_input = gr.Textbox(
                                    placeholder="Ask me anything about the knowledge repository...",
                                    lines=4,
                                    max_lines=12,
                                    show_label=False,
                                    container=False,
                                    interactive=True
                                )
                            with gr.Column(scale=1, min_width=60):
                                submit_btn = gr.Button("Send", variant="primary", elem_classes="send-btn-compact", size="sm")
                                    
                        # Note and send button
                        with gr.Row():
                            gr.Markdown("*Press Shift+Enter to send message, Enter for new line*")
             
            # Files Tab (for all users)
            with gr.TabItem("📄 Files", visible=False) as files_tab:
                with gr.Column(elem_classes="admin-section"):
                    gr.Markdown("## 📚 Document Repository")
                    
                    # Common Knowledge Documents Section
                    with gr.Column():
                        
                        with gr.Row():
                            common_search = gr.Textbox(
                                label="Search Common Documents",
                                placeholder="Search by name, type, or status...",
                                interactive=True,
                                scale=4
                            )
                            refresh_common_btn = gr.Button("🔄 Refresh", variant="secondary", scale=1)
                        
                        common_files_table = gr.Dataframe(
                            label="",
                            headers=["File Name", "Size", "Type", "Uploaded", "Source", "Actions"],
                            datatype=["str", "str", "str", "str", "str", "html"],
                            interactive=False,
                            wrap=True,
                            value=[[""] * 6],
                            row_count=(10, "dynamic"),
                            column_widths=["55%", "6%", "8%", "7%", "12%", "12%"]
                        )

                        gr.Markdown("<br>")
                    
                        # Personal Documents Section
                        with gr.Column(visible=False):
                            
                            with gr.Row():
                                personal_search = gr.Textbox(
                                    label="Search Personal Documents", 
                                    placeholder="Search your documents...",
                                    interactive=True,
                                    scale=4
                                )
                                refresh_personal_btn = gr.Button("🔄 Refresh", variant="secondary", scale=1)
                            
                            personal_files_table = gr.Dataframe(
                                label="",
                                headers=["File Name", "Size", "Type", "Uploaded", "Source", "Actions"],
                                datatype=["str", "str", "str", "str", "str", "html"],
                                interactive=False,
                                wrap=True,
                                value=[],
                                row_count=(10, "dynamic"),
                                column_widths=["55%", "6%", "8%", "7%", "12%", "12%"]
                            )
            
            # File Manager (Common) Tab
            with gr.TabItem("📂 File Manager (Common)", visible=False) as file_manager_common_tab:
                with gr.Column() as file_manager_container:
                    file_manager_title = gr.Markdown("## 📚 Common Knowledge Repository")
                    file_manager_guidelines = gr.Markdown("""
                    **Common Knowledge Repository:**
                    Max file size: 10MB | Formats: .txt, .md, .pdf, .docx | PDFs must be text-extractable
                    """)
                    
                    # Upload/Delete sections (admin only)
                    with gr.Column(visible=False, elem_classes="admin-section") as admin_upload_section:
                        with gr.Row():
                            # Upload section
                            with gr.Column():
                                gr.Markdown("### 📤 Upload Documents")
                                file_upload = gr.File(
                                    label="Select files",
                                    file_types=[".txt", ".md", ".pdf", ".docx"],
                                    file_count="multiple",
                                    type="filepath"
                                )
                                upload_btn = gr.Button("📤 Upload Files", variant="primary")
                            
                            # Delete section
                            with gr.Column():
                                gr.Markdown("### 🗑️ Delete Documents")
                                selected_files = gr.CheckboxGroup(
                                    label="Select files",
                                    choices=[],
                                    value=[]
                                )
                                with gr.Row():
                                    delete_btn = gr.Button("🗑️ Delete Selected", variant="secondary")
                                    select_all_btn = gr.Button("☑️ Select All", variant="secondary")
                    
                    # File list with search
                    gr.Markdown("### 📋 Documents in Knowledge Repository")
                    
                    file_search_box = gr.Textbox(
                        label="Search Files",
                        placeholder="Type to search files by name, type, or status...",
                        interactive=True
                    )
                    
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 Refresh")
                        reindex_btn = gr.Button("🔍 Re-index", variant="primary", visible=False)
                        cleanup_btn = gr.Button("🧹 Cleanup", variant="secondary", visible=False)
                        vector_stats_btn = gr.Button("📊 Vector Stats", variant="secondary")
                    
                    files_table = gr.Dataframe(
                        label="",
                        headers=["File Name", "Size", "Type", "Chunks", "Status", "Uploaded", "Source", "Actions"],
                        datatype=["str", "str", "str", "number", "str", "str", "str", "html"],
                        interactive=False,
                        wrap=True,
                        row_count=(10, "dynamic"),
                        column_widths=["44%", "6%", "8%", "4%", "7%", "7%", "12%", "12%"]
                    )
                    
                    # Status displays
                    upload_status = gr.Textbox(label="Upload Progress", visible=False, lines=6)
                    delete_status = gr.Textbox(label="Delete Progress", visible=False, lines=6)
                    vector_status = gr.Markdown(label="Vector Database Status", visible=False)
            
            # File Manager (Users) Tab
            with gr.TabItem("👥 File Manager (Users)", visible=False) as file_manager_users_tab:
                with gr.Column(elem_classes="admin-section"):
                    gr.Markdown("## Admin User File Management")
                    gr.Markdown("*Manage individual user documents*")
                    
                    # User Selection Section
                    gr.Markdown("### 👤 User Selection")
                    with gr.Row():
                        user_file_users_dropdown = gr.Dropdown(
                            label="Select User",
                            choices=[],
                            value=None,
                            interactive=True,
                            filterable=True,
                            scale=4
                        )
                        refresh_user_file_users_btn = gr.Button("🔄 Refresh Users", variant="secondary", scale=1)
                    
                    user_file_selected_user_info = gr.Markdown("*No user selected*")
                    
                    # File Operations Section
                    gr.Markdown("### 🔧 File Operations")
                    with gr.Row():
                        # Upload section
                        with gr.Column():
                            gr.Markdown("#### 📤 Upload Documents for User")
                            user_file_upload = gr.File(
                                label="Select files",
                                file_types=[".txt", ".md", ".pdf", ".docx"],
                                file_count="multiple",
                                type="filepath"
                            )
                            user_upload_btn = gr.Button("📤 Upload Files", variant="primary")
                        
                        # Delete section
                        with gr.Column():
                            gr.Markdown("#### 🗑️ Delete User Documents")
                            user_selected_files = gr.CheckboxGroup(
                                label="Select files",
                                choices=[],
                                value=[]
                            )
                            with gr.Row():
                                user_delete_btn = gr.Button("🗑️ Delete Selected", variant="secondary")
                                user_select_all_btn = gr.Button("☑️ Select All", variant="secondary")
                    
                    # File Management Controls
                    gr.Markdown("### 🔧 File Management")
                    user_file_search_box = gr.Textbox(
                        label="Search User Files",
                        placeholder="Type to search files by name, type, or status...",
                        interactive=True
                    )
                    
                    with gr.Row():
                        user_refresh_btn = gr.Button("🔄 Refresh")
                        user_reindex_btn = gr.Button("🔍 Re-index", variant="primary", visible=False)
                        user_cleanup_btn = gr.Button("🧹 Cleanup", variant="secondary", visible=False)
                        user_vector_stats_btn = gr.Button("📊 Vector Stats", variant="secondary")
                    
                    # User Files Table
                    user_files_table = gr.Dataframe(
                        label="User Documents",
                        headers=["File Name", "Size", "Type", "Chunks", "Status", "Uploaded", "User", "Actions"],
                        datatype=["str", "str", "str", "number", "str", "str", "str", "html"],
                        interactive=False,
                        wrap=True,
                        row_count=(10, "dynamic"),
                        column_widths=["44%", "6%", "8%", "4%", "7%", "7%", "12%", "12%"]
                    )
                    
                    # Status displays
                    user_upload_status = gr.Textbox(label="Upload Progress", visible=False, lines=6)
                    user_delete_status = gr.Textbox(label="Delete Progress", visible=False, lines=6)
                    user_vector_status = gr.Markdown(label="Vector Database Status", visible=False)
            
            # Users Tab - RESTRUCTURED WITH 3 SUBTABS
            with gr.TabItem("👥 Users", visible=False) as users_tab:
                with gr.Column(elem_classes="admin-section"):
                    gr.Markdown("## Admin User Management")
                    gr.Markdown("*Manage email whitelist, SPOC assignments, and user hierarchy*")
                    
                    with gr.Tabs():
                        # Email Whitelist Subtab
                        with gr.TabItem("📧 Email Whitelist"):
                            gr.Markdown("### Email Whitelist Management")
                            
                            # Department Management Section - MOVED TO TOP
                            with gr.Column(elem_classes="admin-section"):
                                gr.Markdown("#### 🏢 Department Management")
                                with gr.Row():
                                    with gr.Column(scale=1):
                                        gr.Markdown("**Add**")
                                        dept_name_input = gr.Textbox(
                                            label="",
                                            placeholder="Enter department name",
                                            interactive=True
                                        )
                                    add_dept_btn = gr.Button("➕", variant="primary", scale=0, min_width=50)
                                    
                                    with gr.Column(scale=1):
                                        gr.Markdown("**Delete**")
                                        delete_dept_dropdown = gr.Dropdown(
                                            choices=["Select Department"],
                                            value="Select Department",
                                            filterable=True,
                                            label="",
                                            interactive=True
                                        )
                                    delete_dept_btn = gr.Button("🗑️", variant="stop", scale=0, min_width=50)
                                
                                dept_notification = gr.HTML("")
                            
                            # Add Email Section with SPOC/Admin assignment
                            with gr.Row():
                                with gr.Column(scale=1):
                                    gr.Markdown("#### ➕ Add Email to Whitelist")
                                    
                                    # Email and Department side by side
                                    with gr.Row():
                                        whitelist_email_input = gr.Textbox(
                                            label="Email Address",
                                            placeholder="user@sadhguru.org",
                                            interactive=True,
                                            scale=1
                                        )
                                        department_input = gr.Dropdown(
                                            choices=["Select Department"],
                                            value="Select Department",
                                            allow_custom_value=False,
                                            filterable=True,
                                            label="Department (Required)",
                                            interactive=True,
                                            scale=1
                                        )
                                    
                                    email_validation = gr.HTML("")
                                    
                                    # Assignment Type and SPOC dropdown
                                    with gr.Row():
                                        assignment_radio = gr.Radio(
                                            label="Role Assignment",
                                            choices=["Add as User", "Add as SPOC", "Add as Admin"],
                                            value="Add as User",
                                            scale=2
                                        )
                                        
                                        spoc_dropdown = gr.Dropdown(
                                            label="Assign to SPOC (if User)",
                                            choices=["Select SPOC"],
                                            value="Select SPOC",
                                            visible=True,
                                            interactive=True,
                                            scale=2
                                        )
                                    
                                    with gr.Row():
                                        add_to_whitelist_btn = gr.Button("➕ Add Email", variant="primary", scale=1)
                                    
                                    # Notification area
                                    whitelist_notification = gr.HTML("")
                            
                            # Search and Table Section (like files)
                            gr.Markdown("### 📋 Current Email Whitelist")
                            
                            with gr.Row():
                                whitelist_search = gr.Textbox(
                                    placeholder="Search emails, departments...",
                                    label="Search Whitelist",
                                    interactive=True,
                                    scale=4
                                )
                                refresh_whitelist_btn = gr.Button("🔄 Refresh", variant="secondary", scale=1)
                            
                            whitelist_table = gr.Dataframe(
                                headers=["Email", "Role", "Department", "Added By", "Date Added"],
                                datatype=["str", "str", "str", "str", "str"],
                                label="Email Whitelist",
                                interactive=False,
                                wrap=True,
                                row_count=10,
                                column_widths=["25%", "10%", "25%", "20%", "15%"]
                            )
                            
                            # Delete functionality
                            with gr.Row():
                                whitelist_select = gr.Dropdown(
                                    label="Select email to remove",
                                    choices=[],
                                    interactive=True,
                                    scale=4
                                )
                                delete_whitelist_btn = gr.Button("🗑️ Remove", variant="stop", scale=1)
                        
                        # SPOC Assignment Subtab
                        with gr.TabItem("🔧 SPOC Assignment"):
                            gr.Markdown("### SPOC Assignment Management")
                            
                            # Filter and table
                            with gr.Row():
                                spoc_filter_dropdown = gr.Dropdown(
                                    label="Filter by SPOC",
                                    choices=["ALL"],
                                    value="ALL",
                                    interactive=True,
                                    filterable=True,
                                    scale=4
                                )
                                refresh_assignments_btn = gr.Button("🔄", variant="secondary", scale=1, min_width=60)
                            
                            assignments_table = gr.Dataframe(
                                headers=["SPOC Name", "SPOC Email", "User Email", "User Name", "Date Added"],
                                datatype=["str", "str", "str", "str", "str"],
                                label="SPOC Assignments",
                                interactive=False,
                                wrap=True,
                                row_count=10,
                                column_widths=["20%", "25%", "25%", "20%", "10%"]
                            )
                            
                            # Role modification sections
                            gr.Markdown("### 🔧 Role Management")
                            
                            with gr.Row():
                                refresh_roles_btn = gr.Button("🔄 Refresh Roles", variant="secondary", size="sm")
                            
                            with gr.Row():
                                with gr.Column():
                                    gr.Markdown("#### User → SPOC")
                                    user_to_spoc_dropdown = gr.Dropdown(label="Select User", choices=[], filterable=True)
                                    user_to_spoc_btn = gr.Button("⬆️ Promote to SPOC", variant="primary")
                                
                                with gr.Column():
                                    gr.Markdown("#### SPOC → User")
                                    spoc_to_user_dropdown = gr.Dropdown(label="Select SPOC", choices=[], filterable=True)
                                    spoc_to_user_btn = gr.Button("⬇️ Demote to User", variant="secondary")
                            
                            with gr.Row():
                                with gr.Column():
                                    gr.Markdown("#### Transfer User to Another SPOC")
                                    transfer_user_dropdown = gr.Dropdown(label="Select User", choices=[], filterable=True)
                                    current_spoc_display = gr.Textbox(label="Current SPOC", interactive=False, visible=False)
                                    transfer_to_spoc_dropdown = gr.Dropdown(label="Target SPOC", choices=[], filterable=True)
                                    transfer_user_btn = gr.Button("↔️ Transfer", variant="primary")
                                
                                with gr.Column():
                                    gr.Markdown("#### SPOC → Admin")
                                    spoc_to_admin_dropdown = gr.Dropdown(label="Select SPOC", choices=[], filterable=True)
                                    spoc_to_admin_btn = gr.Button("⬆️ Promote to Admin", variant="primary")
                            
                            with gr.Row():
                                with gr.Column():
                                    gr.Markdown("#### Admin → SPOC")
                                    admin_to_spoc_dropdown = gr.Dropdown(label="Select Admin", choices=[], filterable=True)
                                    admin_to_spoc_btn = gr.Button("⬇️ Demote to SPOC", variant="secondary")
                                
                                with gr.Column():
                                    pass  # Empty column for balance
                            
                            spoc_notification = gr.HTML("")
                        
                        # User Hierarchy Subtab
                        with gr.TabItem("👑 User Hierarchy"):
                            gr.Markdown("### Complete User Hierarchy")
                            
                            with gr.Row():
                                role_filter_dropdown = gr.Dropdown(
                                    label="Filter by Role",
                                    choices=["All", "Admin", "SPOC", "User"],
                                    value="All",
                                    interactive=True,
                                    scale=4
                                )
                                refresh_users_btn = gr.Button("🔄", variant="secondary", scale=1, min_width=60)
                            
                            role_users_table = gr.Dataframe(
                                headers=["Name", "Email", "Role", "Added By", "Last Login", "Date Added"],
                                datatype=["str", "str", "str", "str", "str", "str"],
                                label="Users",
                                interactive=False,
                                wrap=True,
                                row_count=10
                            )
        
        # Copyright footer
        gr.HTML("""
        <div style="text-align: center; color: #9ca3af; font-size: 0.875rem; margin-top: 20px; padding: 15px;">
            <p>© Sadhguru, 2025 | This AI chat may make mistakes. Please use with discretion.</p>
        </div>
        """)
        
        # Hidden components for notifications
        file_notification = gr.HTML("")
        action_status = gr.Textbox(visible=False)
        
        # ========== EVENT HANDLERS ==========
        
        def load_common_files_for_tab():
            """Load common knowledge files for Files tab"""
            try:
                return ui_service.get_common_files_for_display()
            except Exception as e:
                print(f"Error loading common files: {e}")
                return []

        def load_personal_files_for_tab():
            """Load personal files for current user"""
            try:
                return ui_service.get_personal_files_for_display()
            except Exception as e:
                print(f"Error loading personal files: {e}")
                return []

        def refresh_common_files():
            """Refresh common knowledge files"""
            try:
                return ui_service.refresh_common_files_display()
            except Exception as e:
                print(f"Error refreshing common files: {e}")
                return []

        def refresh_personal_files():
            """Refresh personal files"""
            try:
                return ui_service.refresh_personal_files_display()
            except Exception as e:
                print(f"Error refreshing personal files: {e}")
                return []

        def search_common_files(search_term):
            """Search common knowledge files"""
            try:
                return ui_service.search_common_files_display(search_term or "")
            except Exception as e:
                print(f"Error searching common files: {e}")
                return []

        def search_personal_files(search_term):
            """Search personal files"""
            try:
                return ui_service.search_personal_files_display(search_term or "")
            except Exception as e:
                print(f"Error searching personal files: {e}")
                return []

        def on_files_tab_select():
            """Load both file sections when Files tab is selected"""
            try:
                return ui_service.load_files_tab_data()
            except Exception as e:
                print(f"Error on files tab select: {e}")
                return [], []


        # Enhanced common knowledge file handlers
        def handle_ck_upload(files):
            """Handle common knowledge file upload"""
            files_list, status, choices, notification = ui_service.handle_common_knowledge_upload(files)
            return (
                gr.update(value=files_list), 
                gr.update(value=status, visible=True), 
                gr.update(choices=choices, value=[]), 
                gr.update(value=notification, visible=True)
            )

        def handle_ck_delete(selected):
            """Handle common knowledge file deletion"""
            files_list, status, choices, notification = ui_service.handle_common_knowledge_delete(selected)
            return (
                gr.update(value=files_list), 
                gr.update(value=status, visible=True), 
                gr.update(choices=choices, value=[]), 
                gr.update(value=notification, visible=True)
            )

        def handle_ck_refresh():
            """Handle common knowledge file refresh"""
            files, choices, notification = ui_service.handle_common_knowledge_refresh()
            return (
                gr.update(value=files), 
                gr.update(choices=choices, value=[]), 
                gr.update(value=notification, visible=True)
            )

        def handle_ck_reindex():
            """Handle common knowledge re-indexing"""
            files, choices, result, notification = ui_service.handle_common_knowledge_reindex()
            return (
                gr.update(value=files), 
                gr.update(choices=choices), 
                result, 
                gr.update(value=notification, visible=True)
            )

        def handle_cleanup_vector_db():
            """Handle cleanup vector database operation"""
            status_msg, notification = ui_service.handle_common_knowledge_cleanup()
            return (
                gr.update(value=status_msg, visible=True), 
                gr.update(value=notification, visible=True)
            )

        def handle_vector_stats():
            """Handle vector database statistics"""
            status_msg, notification = ui_service.handle_common_knowledge_vector_stats()
            return (
                gr.update(value=status_msg, visible=True), 
                gr.update(value=notification, visible=True)
            )

        def handle_file_search(search_term):
            """Handle file search in common knowledge manager"""
            files, choices = ui_service.search_common_knowledge_files(search_term)
            return gr.update(value=files), gr.update(choices=choices, value=[])

        def select_all_files():
            """Select all files in common knowledge manager"""
            if ui_service.is_admin_or_spoc():
                files = enhanced_file_service.get_common_knowledge_file_list()
                all_files = [row[0] for row in files] if files else []
                return gr.update(value=all_files)
            return gr.update(value=[])

        # Enhanced user file manager handlers
        def select_user_for_file_manager(user_email):
            """Select user for file management"""
            if ui_service.is_admin() and user_email:
                users = user_management.get_all_users()
                user_info = next((u for u in users if u['email'] == user_email), None)
                if user_info:
                    info_text = f"**Selected User:** {user_info['name']} ({user_info['email']})\n"
                    info_text += f"**Role:** {user_info['role'].upper()}\n"
                    info_text += f"**Last Login:** {user_info.get('last_login', 'Never')[:10] if user_info.get('last_login') else 'Never'}"
                    
                    # Load user files
                    files, choices, _ = ui_service.handle_user_file_refresh(user_email)
                    
                    return (
                        gr.update(value=info_text),
                        gr.update(value=files),
                        gr.update(choices=choices, value=[])
                    )
            return (
                gr.update(value="*No user selected*"),
                gr.update(value=[]),
                gr.update(choices=[], value=[])
            )

        def handle_user_file_upload(user_email, files):
            """Handle user file upload"""
            files_list, status, choices, notification = ui_service.handle_user_file_upload(user_email, files)
            return (
                gr.update(value=files_list), 
                gr.update(value=status, visible=True), 
                gr.update(choices=choices), 
                gr.update(value=notification, visible=True)
            )

        def handle_user_file_delete(user_email, selected_files):
            """Handle user file deletion"""
            files_list, status, choices, notification = ui_service.handle_user_file_delete(user_email, selected_files)
            return (
                gr.update(value=files_list), 
                gr.update(value=status, visible=True), 
                gr.update(choices=choices), 
                gr.update(value=notification, visible=True)
            )

        def handle_user_file_refresh(user_email):
            """Handle user file refresh"""
            files, choices, notification = ui_service.handle_user_file_refresh(user_email)
            return (
                gr.update(value=files), 
                gr.update(choices=choices, value=[]), 
                gr.update(value=notification, visible=True)
            )

        def handle_user_reindex(user_email):
            """Handle user file re-indexing"""
            result, notification = ui_service.handle_user_file_reindex(user_email)
            return (
                gr.update(value=result, visible=True), 
                gr.update(value=notification, visible=True)
            )

        def handle_user_cleanup_vector_db(user_email):
            """Handle user vector cleanup"""
            status_msg, notification = ui_service.handle_user_vector_cleanup(user_email)
            return (
                gr.update(value=status_msg, visible=True), 
                gr.update(value=notification, visible=True)
            )

        def handle_user_vector_stats(user_email):
            """Handle user vector stats"""
            status_msg, notification = ui_service.handle_user_vector_stats(user_email)
            return (
                gr.update(value=status_msg, visible=True), 
                gr.update(value=notification, visible=True)
            )

        def handle_user_file_search(user_email, search_term):
            """Handle user file search"""
            files, choices = ui_service.search_user_files(user_email, search_term)
            return gr.update(value=files), gr.update(choices=choices, value=[])

        def select_all_user_files(user_email):
            """Select all user files"""
            if ui_service.is_admin() and user_email:
                user_files = enhanced_file_service.get_user_file_list(user_email)
                all_files = [row[0] for row in user_files] if user_files else []
                return gr.update(value=all_files)
            return gr.update(value=[])

        def refresh_user_file_users():
            """Refresh user dropdown for file management"""
            if ui_service.is_admin():
                users = user_management.get_all_users()
                user_choices = [(user_management.format_user_for_dropdown(user), user['email']) for user in users]
                notification = '<div class="notification">🔄 Users refreshed</div>'
                return gr.update(choices=user_choices), gr.update(value=notification, visible=True)
            return gr.update(choices=[]), gr.update(value="Access denied", visible=True)

        # ========== LOAD INITIAL DATA ==========
        
        # Enhanced initial visibility function
        def get_initial_visibility():
            """Get tab visibility based on user role - ENHANCED VERSION"""
            user_role = ui_service.get_user_role()
            user_email = ui_service.current_user.get("email", "")
            
            if user_role == "admin":
                greeting = f"Namaskaram {ui_service.get_display_name()}! [ADMIN]"
            elif user_role == "spoc":
                greeting = f"Namaskaram {ui_service.get_display_name()}! [SPOC]"
            else:
                greeting = f"Namaskaram {ui_service.get_display_name()}!"
            
            # Load initial chat data and default conversation for admin/SPOC
            _, sessions_update = ui_service.load_initial_data()
            
            # For admin/SPOC, try to load their own conversations by default
            default_chat_user = None
            if user_role in ["admin", "spoc"]:
                default_chat_user = user_email
            
            # Tab visibility - Files tab visible for all users
            files_tab_visible = True
            file_manager_common_visible = user_role in ["admin", "spoc"]
            file_manager_users_visible = user_role == "admin"
            users_tab_visible = user_role == "admin"
            
            # Section visibility within tabs
            admin_chat_section_visible = user_role in ["admin", "spoc"]
            admin_upload_section_visible = user_role == "admin"
            reindex_visible = user_role == "admin"
            cleanup_visible = user_role == "admin"
            
            # User file manager button visibility
            user_reindex_visible = user_role == "admin"
            user_cleanup_visible = user_role == "admin"
            
            # Title and styling
            if user_role == "spoc":
                title_text = "## SPOC File Management"
                container_class = "spoc-section"
            else:
                title_text = "## Common Knowledge Repository"
                container_class = "admin-section"
            
            guidelines_text = """
            **Common Knowledge Repository:**
            Max file size: 10MB | Formats: .txt, .md, .pdf, .docx | PDFs must be text-extractable
            """
            
            return (
                greeting,
                sessions_update,
                gr.update(visible=files_tab_visible),
                gr.update(visible=file_manager_common_visible),
                gr.update(visible=file_manager_users_visible),
                gr.update(visible=users_tab_visible),
                gr.update(visible=admin_chat_section_visible),
                gr.update(visible=admin_upload_section_visible),
                gr.update(visible=reindex_visible),
                gr.update(visible=cleanup_visible),
                gr.update(value=title_text),
                gr.update(value=guidelines_text),
                gr.update(elem_classes=container_class),
                gr.update(value=default_chat_user),
                gr.update(visible=user_reindex_visible),
                gr.update(visible=user_cleanup_visible)
            )

        # Load initial data
        demo.load(
            fn=get_initial_visibility, 
            outputs=[
                namaskaram_user, sessions_radio, files_tab, file_manager_common_tab,
                file_manager_users_tab, users_tab, admin_chat_user_section,
                admin_upload_section, reindex_btn, cleanup_btn,
                file_manager_title, file_manager_guidelines, file_manager_container,
                chat_users_dropdown, user_reindex_btn, user_cleanup_btn
            ]
        )

        def show_welcome_if_needed():
            """Show welcome message for first-time users"""
            return None

        # Add separate welcome check
        demo.load(
            fn=show_welcome_if_needed,
            js="""
            function() {
                // Simple check - if URL has welcome=true, show message
                if (window.location.search.includes('welcome=true')) {
                    
                    // Create welcome overlay
                    const overlay = document.createElement('div');
                    overlay.style.cssText = `
                        position: fixed;
                        top: 0; left: 0; right: 0; bottom: 0;
                        background: rgba(0,0,0,0.5);
                        z-index: 10000;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    `;
                    
                    const welcomeBox = document.createElement('div');
                    welcomeBox.innerHTML = 'Namaskaram! Welcome to Isha Sevabot';
                    welcomeBox.style.cssText = `
                        background: white;
                        padding: 3rem 4rem;
                        border-radius: 20px;
                        text-align: center;
                        font-size: 1.5rem;
                        font-weight: 600;
                        color: #333;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        transform: scale(0.8);
                        transition: transform 0.3s ease;
                    `;
                    
                    overlay.appendChild(welcomeBox);
                    document.body.appendChild(overlay);
                    
                    // Animate in
                    setTimeout(() => {
                        welcomeBox.style.transform = 'scale(1)';
                    }, 100);
                    
                    // Remove after 3 seconds
                    setTimeout(() => {
                        overlay.style.opacity = '0';
                        overlay.style.transition = 'opacity 0.5s ease';
                        setTimeout(() => {
                            document.body.removeChild(overlay);
                        }, 500);
                    }, 3000);
                    
                    // Clean up URL
                    window.history.replaceState({}, document.title, window.location.pathname);
                }
            }
            """
        )
        
        # Load user files for regular users
        demo.load(fn=on_files_tab_select, outputs=[common_files_table, personal_files_table])

        # Load admin data
        def load_admin_data():
            if ui_service.is_admin():
                # Common knowledge files
                files = enhanced_file_service.get_common_knowledge_file_list()
                choices = [row[0] for row in files] if files else []
                
                # Users data
                users = user_management.get_all_users()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_users_for_chat = [user for user in users if user['role'] in ['user', 'spoc', 'admin']]
                
                # Assignable users (from whitelist, excluding already assigned)
                assignable_users = user_management.get_assignable_users_for_spoc()
                
                all_user_choices = [(user_management.format_user_for_dropdown(user) + f" - {user['role'].upper()}", user['email']) for user in users]
                spoc_choices = [("Select SPOC...", "")] + [(user_management.format_user_for_dropdown(user), user['email']) for user in spoc_users]
                assignable_choices = [("Select User...", "")] + [(user_management.format_user_for_dropdown(user), user['email']) for user in assignable_users]
                chat_user_choices = [(user_management.format_user_for_dropdown(user), user['email']) for user in all_users_for_chat]
                
                user_file_choices = [(user_management.format_user_for_dropdown(user), user['email']) for user in users]
                admin_users_table = user_management.get_users_by_role("admin")
                
                # Whitelist data with roles
                whitelist_data = user_management.get_whitelisted_emails_with_roles()
                whitelist_table_data = []
                whitelist_choices = []
                for item in whitelist_data:
                    whitelist_table_data.append([
                        item["email"],
                        item.get("role", "user"),
                        item.get("department", ""), 
                        item["added_by"], 
                        item["added_at"][:10]
                    ])
                    whitelist_choices.append(item["email"])

                departments_list = ["Select Department"] + user_management.get_departments()
                spoc_list = ["Select SPOC"] + user_management.get_spoc_users()
                assignments_data = user_management.get_assignments_with_names("ALL")
                
                # Get role-based choices for new SPOC management
                regular_users = [u for u in users if u['role'] == 'user']
                spoc_users_for_mgmt = [u for u in users if u['role'] == 'spoc']
                admin_users_for_mgmt = [u for u in users if u['role'] == 'admin']
                
                user_choices_mgmt = [(user_management.format_user_for_dropdown(u), u['email']) for u in regular_users]
                spoc_choices_mgmt = [(user_management.format_user_for_dropdown(u), u['email']) for u in spoc_users_for_mgmt]
                admin_choices_mgmt = [(user_management.format_user_for_dropdown(u), u['email']) for u in admin_users_for_mgmt]
                
                # Get SPOC emails for filter dropdown
                spoc_filter_choices = ["ALL"] + [u['email'] for u in spoc_users_for_mgmt]
                
                # Get user hierarchy data - use get_all_users_table which has proper formatting
                users_hierarchy = user_management.get_all_users_table()
                
                return (
                    gr.update(value=files), gr.update(choices=choices, value=[]),  # files_table, selected_files
                    gr.update(choices=chat_user_choices), gr.update(choices=user_file_choices),  # chat_users_dropdown, user_file_users_dropdown
                    gr.update(value=users_hierarchy),  # role_users_table
                    gr.update(value=whitelist_table_data),  # whitelist_table
                    gr.update(choices=departments_list, value="Select Department"),  # department_input
                    gr.update(choices=departments_list, value="Select Department"),  # delete_dept_dropdown
                    gr.update(value=assignments_data),  # assignments_table
                    gr.update(choices=spoc_list, value="Select SPOC"),  # spoc_dropdown - FIXED
                    gr.update(choices=whitelist_choices),  # whitelist_select
                    gr.update(choices=spoc_filter_choices),  # spoc_filter_dropdown
                    gr.update(choices=user_choices_mgmt, value=None),  # user_to_spoc_dropdown
                    gr.update(choices=spoc_choices_mgmt, value=None),  # spoc_to_user_dropdown
                    gr.update(choices=user_choices_mgmt, value=None),  # transfer_user_dropdown
                    gr.update(choices=spoc_choices_mgmt, value=None),  # transfer_to_spoc_dropdown
                    gr.update(choices=spoc_choices_mgmt, value=None),  # spoc_to_admin_dropdown
                    gr.update(choices=admin_choices_mgmt, value=None)  # admin_to_spoc_dropdown
                )
            elif ui_service.is_spoc():
                files = enhanced_file_service.get_common_knowledge_file_list()
                assigned_users = user_management.get_spoc_assignments(ui_service.current_user["email"])
                users = user_management.get_all_users()
                assigned_user_details = [user for user in users if user['email'] in assigned_users]
                chat_user_choices = [(user_management.format_user_for_dropdown(user), user['email']) for user in assigned_user_details]
                
                return tuple([gr.update(value=files)] + [gr.update()] * 2 + [gr.update(choices=chat_user_choices)] + [gr.update()] * 14)
            
            return tuple([gr.update()] * 18)
        
        demo.load(
            fn=load_admin_data,
            outputs=[
                files_table, selected_files,
                chat_users_dropdown, user_file_users_dropdown, role_users_table,
                whitelist_table, department_input, delete_dept_dropdown,
                assignments_table, spoc_dropdown, whitelist_select,
                spoc_filter_dropdown, user_to_spoc_dropdown, spoc_to_user_dropdown,
                transfer_user_dropdown, transfer_to_spoc_dropdown, spoc_to_admin_dropdown,
                admin_to_spoc_dropdown
            ]
        )
        
        # Load assignments overview
        def load_assignments_overview():
            if ui_service.is_admin():
                return gr.update(value=user_management.get_assignments_overview_table())
            return gr.update(value=[])
        
        demo.load(fn=load_assignments_overview, outputs=[assignments_table])
        
        # ========== CHAT HANDLERS ==========
        
        # Chat user selection with proper conversation loading
        def select_user_for_chat(selected_user_email):
            if not ui_service.is_admin_or_spoc() or not selected_user_email:
                return gr.update(), selected_user_email
            
            # Get conversations for the selected user
            if ui_service.is_admin():
                conversations = chat_service.get_user_conversations(selected_user_email)
            elif ui_service.is_spoc():
                # Check if SPOC has access to this user
                assigned_users = user_management.get_spoc_assignments(ui_service.current_user["email"])
                if selected_user_email not in assigned_users:
                    return gr.update(), None
                conversations = chat_service.get_user_conversations(selected_user_email)
            else:
                return gr.update(), None
            
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            
            return gr.update(choices=session_choices, value=None), selected_user_email
        
        def refresh_chat_users():
            if ui_service.is_admin():
                users = user_management.get_all_users()
                all_users_for_chat = [user for user in users if user['role'] in ['user', 'spoc', 'admin']]
                chat_user_choices = [(user_management.format_user_for_dropdown(user), user['email']) for user in all_users_for_chat]
                return gr.update(choices=chat_user_choices)
            elif ui_service.is_spoc():
                assigned_users = user_management.get_spoc_assignments(ui_service.current_user["email"])
                users = user_management.get_all_users()
                assigned_user_details = [user for user in users if user['email'] in assigned_users]
                chat_user_choices = [(user_management.format_user_for_dropdown(user), user['email']) for user in assigned_user_details]
                return gr.update(choices=chat_user_choices)
            
            return gr.update(choices=[])
        
        def refresh_current_user_chats():
            conversations = chat_service.get_user_conversations(ui_service.current_user["email"])
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            return gr.update(choices=session_choices, value=None)
        
        chat_users_dropdown.change(fn=select_user_for_chat, inputs=[chat_users_dropdown], outputs=[sessions_radio, selected_chat_user])
        refresh_chat_users_btn.click(fn=refresh_chat_users, outputs=[chat_users_dropdown])
        refresh_chat_btn.click(fn=refresh_current_user_chats, outputs=[sessions_radio])

        def send_message_with_radio_disable(message, history, conversation_id, target_user, pending_feedback_state):
            # Block sending if feedback is pending
            if pending_feedback_state:
                notification = '<div class="notification" style="background: #f59e0b !important;">⚠️ Please provide feedback before sending a new message</div>'
                return history, "", conversation_id, gr.update(), "", gr.update(interactive=False), gr.update(visible=True), None, True, gr.update(interactive=False), gr.update(interactive=False), notification
            
            result = ui_service.send_message_for_user(message, history, conversation_id, target_user)
            return result + (gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False), gr.update(value="", visible=False))

        chat_input.submit(
            fn=send_message_with_radio_disable, 
            inputs=[chat_input, chatbot, current_conversation_id, selected_chat_user, pending_feedback], 
            outputs=[chatbot, chat_input, current_conversation_id, sessions_radio, action_status, chat_input, feedback_row, last_assistant_message_id, pending_feedback, sessions_radio, new_chat_btn, file_notification]
        )

        submit_btn.click(
            fn=send_message_with_radio_disable, 
            inputs=[chat_input, chatbot, current_conversation_id, selected_chat_user, pending_feedback], 
            outputs=[chatbot, chat_input, current_conversation_id, sessions_radio, action_status, chat_input, feedback_row, last_assistant_message_id, pending_feedback, sessions_radio, new_chat_btn, file_notification]
        )

        # Navigation blocking functions
        def show_feedback_warning(action_name):
            """Show warning notification for pending feedback"""
            warning_message = f'<div class="notification">⚠️ Please provide feedback for the previous response before {action_name}</div>'
            return gr.update(value=warning_message, visible=True)
        
        def safe_new_chat(target_user, pending_feedback_state):
            """Create new chat only if no feedback is pending and under session limit"""
            from constants import MAX_SESSIONS_PER_USER, ERROR_MESSAGES
            
            # Determine user email
            user_email = target_user if target_user and ui_service.is_admin_or_spoc() else ui_service.current_user["email"]
            
            # Check pending feedback first
            if pending_feedback_state:
                notification = show_feedback_warning("creating a new chat")
                conversations = chat_service.get_user_conversations(user_email)
                if conversations:
                    has_pending, _, pending_conv_id = ui_service.check_pending_feedback()
                    if has_pending and pending_conv_id:
                        history, conv_id, _ = ui_service.load_conversation_for_user(pending_conv_id, target_user)
                        return history, conv_id, gr.update(), "Please provide feedback first", True, notification, gr.update(interactive=False)
                
                return [], None, gr.update(), "Please provide feedback first", pending_feedback_state, notification, gr.update(interactive=False)
            
            # Get existing conversations
            existing_conversations = chat_service.get_user_conversations(user_email)
            
            # Check session limit
            if len(existing_conversations) >= MAX_SESSIONS_PER_USER:
                session_choices = [(conv["title"], conv["id"]) for conv in existing_conversations]
                
                # Create max session notification
                max_session_notification = f'<div class="notification" style="background: #f59e0b !important;">⚠️ Maximum {MAX_SESSIONS_PER_USER} sessions reached. Please delete a conversation first.</div>'
                
                # Load most recent conversation if exists
                if existing_conversations:
                    latest_conv_id = existing_conversations[0]["id"]
                    history, conv_id, _ = ui_service.load_conversation_for_user(latest_conv_id, target_user)
                    return (
                        history, 
                        conv_id, 
                        gr.update(choices=session_choices, value=conv_id), 
                        ERROR_MESSAGES["session_limit"], 
                        False, 
                        gr.update(value=max_session_notification, visible=True), 
                        gr.update(interactive=True)
                    )
                
                # No conversations exist but somehow at limit (shouldn't happen)
                return (
                    [], 
                    None, 
                    gr.update(choices=session_choices, value=None), 
                    ERROR_MESSAGES["session_limit"], 
                    False, 
                    gr.update(value=max_session_notification, visible=True), 
                    gr.update(interactive=True)
                )
            
            # Proceed with creating new chat (under limit)
            result = ui_service.create_new_chat_for_user(target_user)
            empty_notification = gr.update(value="", visible=False)
            return result + (False, empty_notification, gr.update(interactive=True))

        def safe_load_conversation(conversation_id, target_user, pending_feedback_state, current_conv_id):
            """Load conversation only if no feedback is pending"""
            if pending_feedback_state:
                notification = show_feedback_warning("switching conversations")
                # Return current conversation ID to prevent switching
                return [], current_conv_id, "Please provide feedback first", notification
            
            result = ui_service.load_conversation_for_user(conversation_id, target_user)
            empty_notification = gr.update(value="", visible=False)
            return result + (empty_notification,)

        def safe_delete_conversation(conversation_id, target_user, pending_feedback_state):
            """Delete conversation only if no feedback is pending"""
            if pending_feedback_state:
                notification = show_feedback_warning("deleting conversations")
                return [], conversation_id, gr.update(), "Please provide feedback first", notification
            
            result = ui_service.delete_conversation_for_user(conversation_id, target_user)
            empty_notification = gr.update(value="", visible=False)
            return result + (empty_notification,)
        
        def show_max_sessions_notification():
            """Show notification after clearing"""
            from constants import MAX_SESSIONS_PER_USER
            return gr.update(value=f'<div class="notification">⚠️ Maximum {MAX_SESSIONS_PER_USER} sessions reached. Delete a conversation first.</div>')
                
        # Session management
        # Update the new chat button binding to disable the button itself
        new_chat_btn.click(
            fn=safe_new_chat, 
            inputs=[selected_chat_user, pending_feedback], 
            outputs=[chatbot, current_conversation_id, sessions_radio, action_status, pending_feedback, file_notification, new_chat_btn]
        ).then(
            fn=show_max_sessions_notification,
            outputs=[file_notification]
        )
        
        delete_chat_btn.click(fn=safe_delete_conversation, inputs=[sessions_radio, selected_chat_user, pending_feedback], outputs=[chatbot, current_conversation_id, sessions_radio, action_status, file_notification])

        sessions_radio.change(fn=safe_load_conversation, inputs=[sessions_radio, selected_chat_user, pending_feedback, current_conversation_id], outputs=[chatbot, current_conversation_id, action_status, file_notification])

        # ========== FILE MANAGEMENT EVENT BINDINGS ==========
        
        # Files tab bindings (for all users)
        files_tab.select(fn=on_files_tab_select, outputs=[common_files_table, personal_files_table])
        refresh_common_btn.click(fn=refresh_common_files, outputs=[common_files_table])
        refresh_personal_btn.click(fn=refresh_personal_files, outputs=[personal_files_table])
        common_search.change(fn=search_common_files, inputs=[common_search], outputs=[common_files_table])
        personal_search.change(fn=search_personal_files, inputs=[personal_search], outputs=[personal_files_table])

        # Common knowledge file operations
        upload_btn.click(fn=handle_ck_upload, inputs=[file_upload], outputs=[files_table, upload_status, selected_files, file_notification])
        delete_btn.click(fn=handle_ck_delete, inputs=[selected_files], outputs=[files_table, delete_status, selected_files, file_notification])
        refresh_btn.click(fn=handle_ck_refresh, outputs=[files_table, selected_files, file_notification])
        reindex_btn.click(fn=handle_ck_reindex, outputs=[files_table, selected_files, action_status, file_notification])
        cleanup_btn.click(fn=handle_cleanup_vector_db, outputs=[vector_status, file_notification])
        vector_stats_btn.click(fn=handle_vector_stats, outputs=[vector_status, file_notification])
        file_search_box.change(fn=handle_file_search, inputs=[file_search_box], outputs=[files_table, selected_files])
        select_all_btn.click(fn=select_all_files, outputs=[selected_files])

        # User file manager operations
        refresh_user_file_users_btn.click(fn=refresh_user_file_users, outputs=[user_file_users_dropdown, file_notification])
        user_file_users_dropdown.change(fn=select_user_for_file_manager, inputs=[user_file_users_dropdown], outputs=[user_file_selected_user_info, user_files_table, user_selected_files]).then(fn=lambda email: email, inputs=[user_file_users_dropdown], outputs=[selected_user_for_file_manager])
        user_upload_btn.click(fn=handle_user_file_upload, inputs=[selected_user_for_file_manager, user_file_upload], outputs=[user_files_table, user_upload_status, user_selected_files, file_notification])
        user_delete_btn.click(fn=handle_user_file_delete, inputs=[selected_user_for_file_manager, user_selected_files], outputs=[user_files_table, user_delete_status, user_selected_files, file_notification])
        user_refresh_btn.click(fn=handle_user_file_refresh, inputs=[selected_user_for_file_manager], outputs=[user_files_table, user_selected_files, file_notification])
        user_reindex_btn.click(fn=handle_user_reindex, inputs=[selected_user_for_file_manager], outputs=[user_vector_status, file_notification])
        user_cleanup_btn.click(fn=handle_user_cleanup_vector_db, inputs=[selected_user_for_file_manager], outputs=[user_vector_status, file_notification])
        user_vector_stats_btn.click(fn=handle_user_vector_stats, inputs=[selected_user_for_file_manager], outputs=[user_vector_status, file_notification])
        user_file_search_box.change(fn=handle_user_file_search, inputs=[selected_user_for_file_manager, user_file_search_box], outputs=[user_files_table, user_selected_files])
        user_select_all_btn.click(fn=select_all_user_files, inputs=[selected_user_for_file_manager], outputs=[user_selected_files])

        # ========== USER MANAGEMENT HANDLERS - RESTRUCTURED ==========
        
        # Role management with restructured buttons
        def promote_user_to_spoc(user_email):
            if not ui_service.is_admin() or not user_email:
                notification = '<div class="notification">❌ Please select a user</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)
            
            success = user_management.promote_user_to_spoc(user_email)
            if success:
                users = user_management.get_all_users()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_user_choices = [(user_management.format_user_for_dropdown(user) + f" - {user['role'].upper()}", user['email']) for user in users]
                spoc_choices = [("Select SPOC...", "")] + [(user_management.format_user_for_dropdown(user), user['email']) for user in spoc_users]
                
                role_data = user_management.get_users_by_role("admin")
                assignments_data = user_management.get_assignments_overview_table()
                
                notification = '<div class="notification">✅ User modified as SPOC successfully</div>'
                return (
                    gr.update(choices=all_user_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(value=role_data),
                    gr.update(value=assignments_data),
                    gr.update(value=notification, visible=True)
                )
            else:
                notification = '<div class="notification">❌ Failed to modify user as SPOC</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)

        def demote_spoc_to_user(spoc_email, reassign_email=None):
            if not ui_service.is_admin() or not spoc_email:
                notification = '<div class="notification">❌ Please select a SPOC</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)
            
            success = user_management.demote_spoc_to_user(spoc_email, reassign_email)
            if success:
                users = user_management.get_all_users()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_user_choices = [(user_management.format_user_for_dropdown(user) + f" - {user['role'].upper()}", user['email']) for user in users]
                spoc_choices = [("Select SPOC...", "")] + [(user_management.format_user_for_dropdown(user), user['email']) for user in spoc_users]
                
                role_data = user_management.get_users_by_role("admin")
                assignments_data = user_management.get_assignments_overview_table()
                
                notification = '<div class="notification">✅ SPOC modified as user successfully</div>'
                return (
                    gr.update(choices=all_user_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(value=role_data),
                    gr.update(value=assignments_data),
                    gr.update(value=notification, visible=True)
                )
            else:
                notification = '<div class="notification">❌ Failed to modify SPOC as user</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)

        def update_role_sections_visibility(action):
            """Show/hide promote/demote sections based on selected action"""
            if action == "Modify User as SPOC":
                return gr.update(visible=True), gr.update(visible=False)
            else:
                return gr.update(visible=False), gr.update(visible=True)

        def update_role_table(role):
            """Update role table with fresh data"""
            if not ui_service.is_admin():
                return gr.update()
            fresh_data = user_management.get_users_by_role(role)
            return gr.update(value=fresh_data)

        # Email validation function
        def validate_email_input(email):
            """Validate email and show dynamic feedback"""
            if not email:
                return ""
            
            email = email.strip().lower()
            
            if not email:
                return ""
            
            if "@" not in email:
                return '<div style="color: #ef4444; padding: 5px;">⚠️ Please enter a valid email format</div>'
            
            if not email.endswith("@sadhguru.org"):
                return '<div style="color: #ef4444; padding: 5px;">❌ Only @sadhguru.org emails are allowed</div>'
            
            # Valid domain
            return '<div style="color: #10b981; padding: 5px;">✅ Valid domain - ready to add</div>'

        # Whitelist search function with roles
        def search_whitelist_data(search_term):
            """Search whitelist and update table + dropdown"""
            try:
                if not ui_service.is_admin():
                    return gr.update(), gr.update()
                
                whitelist_data = user_management.get_whitelisted_emails_with_roles()
                
                if search_term and search_term.strip():
                    search_lower = search_term.lower().strip()
                    filtered_data = [
                        item for item in whitelist_data 
                        if (search_lower in item["email"].lower() or 
                            search_lower in item.get("department", "").lower() or
                            search_lower in item["added_by"].lower())
                    ]
                else:
                    filtered_data = whitelist_data
                
                # Format table data with role
                table_data = []
                dropdown_choices = []
                for item in filtered_data:
                    table_data.append([
                        item["email"],
                        item.get("role", "user"),
                        item.get("department", ""), 
                        item["added_by"], 
                        item["added_at"][:10]
                    ])
                    dropdown_choices.append(item["email"])
                
                return gr.update(value=table_data), gr.update(choices=dropdown_choices)
                
            except Exception as e:
                print(f"Error searching whitelist: {e}")
                return gr.update(), gr.update()

        def refresh_whitelist_data():
            """Refresh whitelist table"""
            return search_whitelist_data("")

        # Delete single email function
        def delete_single_email(email):
            """Delete a single email from whitelist"""
            if not ui_service.is_admin() or not email:
                return gr.update(), gr.update(), gr.update(), '<div class="notification">❌ Access denied or invalid email</div>'
            
            if user_management.remove_email_from_whitelist(email):
                table_update, dropdown_update = search_whitelist_data("")
                notification = '<div class="notification">✅ Email removed from whitelist</div>'
                return table_update, dropdown_update, gr.update(value=None), notification
            else:
                return gr.update(), gr.update(), gr.update(), '<div class="notification">❌ Failed to remove email</div>'

        # Whitelist management with mandatory department and SPOC assignment
        def add_email_to_whitelist_handler(email, department, assignment, spoc):
            """Add email to whitelist with proper validation and role assignment"""
            if not ui_service.is_admin():
                notification = '<div class="notification" style="background: #ef4444 !important;">❌ Admin access required</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), notification

            if not email or not email.strip():
                notification = '<div class="notification" style="background: #f59e0b !important;">⚠️ Please enter an email address</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), notification

            # Department required only for regular users
            if assignment == "Add as User":
                if not department or department.strip() == "" or department == "Select Department":
                    notification = '<div class="notification" style="background: #f59e0b !important;">⚠️ Department is mandatory for regular users</div>'
                    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), notification
                
                # SPOC validation for regular users
                if not spoc or spoc.strip() == "" or spoc == "Select SPOC":
                    notification = '<div class="notification" style="background: #f59e0b !important;">⚠️ Please select a SPOC for user assignment</div>'
                    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), notification

            # Validate domain
            email_clean = email.strip().lower()
            if not email_clean.endswith("@sadhguru.org"):
                notification = '<div class="notification" style="background: #ef4444 !important;">❌ Only @sadhguru.org emails are allowed</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), notification

            try:
                # Pass empty string for department if not selected or not required
                dept_to_pass = department.strip() if department and department != "Select Department" else ""
                spoc_to_pass = spoc if assignment == "Add as User" else ""
                notification = ui_service.add_user_complete_workflow(email_clean, dept_to_pass, assignment, spoc_to_pass)
                
                if "✅" in notification:
                    # Refresh all data
                    table_update, dropdown_update = search_whitelist_data("")
                    departments_list = ["Select Department"] + user_management.get_departments()
                    
                    # Get fresh SPOC list
                    spoc_users = user_management.get_all_users()
                    spoc_list = ["Select SPOC"] + [s['email'] for s in spoc_users if s['role'] == 'spoc']
                    
                    return (
                        table_update,
                        dropdown_update,
                        gr.update(choices=departments_list, value="Select Department"),
                        gr.update(value=""),  # Clear email input
                        gr.update(value="Add as User"),  # Reset assignment radio
                        gr.update(choices=spoc_list, visible=True, value="Select SPOC"),
                        notification
                    )
                else:
                    # Return notification without clearing inputs so user can fix and retry
                    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), notification
            except Exception as e:
                notification = f'<div class="notification" style="background: #ef4444 !important;">❌ Error: {str(e)}</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), notification
        
        # Department management handlers
        def add_department_handler(dept_name):
            """Add a new department"""
            if not ui_service.is_admin() or not dept_name or not dept_name.strip():
                return gr.update(), gr.update(), '<div class="notification">❌ Invalid department name</div>'
            
            success, message = user_management.add_department(dept_name, ui_service.current_user["email"])
            if success:
                departments_list = ["Select Department"] + user_management.get_departments()
                notification = f'<div class="notification">✅ {message}</div>'
                return (
                    gr.update(choices=departments_list, value="Select Department"),  # department_input
                    gr.update(choices=departments_list, value="Select Department"),  # delete_dept_dropdown
                    notification
                )
            else:
                notification = f'<div class="notification">❌ {message}</div>'
                return gr.update(), gr.update(), notification
        
        def delete_department_handler(dept_name):
            """Delete a department"""
            if not ui_service.is_admin() or not dept_name or dept_name == "Select Department":
                return gr.update(), gr.update(), '<div class="notification">❌ Please select a department to delete</div>'
            
            success, message = user_management.delete_department(dept_name)
            if success:
                departments_list = ["Select Department"] + user_management.get_departments()
                notification = f'<div class="notification">✅ {message}</div>'
                return (
                    gr.update(choices=departments_list, value="Select Department"),  # department_input
                    gr.update(choices=departments_list, value="Select Department"),  # delete_dept_dropdown
                    notification
                )
            else:
                notification = f'<div class="notification">❌ {message}</div>'
                return gr.update(), gr.update(), notification
        
        # SPOC Assignment handlers
        def filter_spoc_assignments(spoc_filter):
            """Filter assignments by SPOC"""
            if not ui_service.is_admin():
                return gr.update()
            
            assignments = user_management.get_assignments_with_names(spoc_filter)
            return gr.update(value=assignments[:10])
        
        def refresh_spoc_assignments():
            """Refresh all assignments"""
            return filter_spoc_assignments("ALL")
        
        def promote_user_to_spoc_handler(user_email):
            """Promote user to SPOC"""
            if not ui_service.is_admin() or not user_email:
                return tuple([gr.update(value=None)] * 5 + [gr.update()] + ['<div class="notification" style="background: #ef4444 !important;">❌ Please select a user</div>'])
            
            try:
                print(f"Promoting {user_email} to SPOC")
                success = user_management.update_user_role(user_email, USER_ROLES['spoc'])
                if success:
                    print(f"✅ Successfully promoted {user_email}")
                    # Refresh all dropdowns with clean formatting
                    user_choices = user_management.get_dropdown_choices_by_role('user')
                    spoc_choices = user_management.get_dropdown_choices_by_role('spoc')
                    admin_choices = user_management.get_dropdown_choices_by_role('admin')
                    
                    # Get updated assignments
                    assignments_data = user_management.get_assignments_overview_table()
                    
                    notification = '<div class="notification" style="background: #10b981 !important;">✅ User promoted to SPOC successfully</div>'
                    
                    return (
                        gr.update(choices=user_choices, value=None),  # user_to_spoc_dropdown
                        gr.update(choices=spoc_choices, value=None),  # spoc_to_user_dropdown
                        gr.update(choices=spoc_choices, value=None),  # spoc_to_admin_dropdown
                        gr.update(choices=admin_choices, value=None),  # admin_to_spoc_dropdown
                        gr.update(choices=spoc_choices, value=None),  # transfer_to_spoc_dropdown
                        gr.update(value=assignments_data),  # assignments_table
                        notification
                    )
                else:
                    print(f"❌ Failed to promote {user_email}")
                    notification = '<div class="notification" style="background: #ef4444 !important;">❌ Failed to promote user</div>'
                    return tuple([gr.update(value=None)] * 5 + [gr.update()] + [notification])
            except Exception as e:
                print(f"Error promoting user: {e}")
                notification = f'<div class="notification" style="background: #ef4444 !important;">❌ Error: {str(e)}</div>'
                return tuple([gr.update(value=None)] * 5 + [gr.update()] + [notification])

        def demote_spoc_to_user_handler(spoc_email):
            """Demote SPOC to user"""
            if not ui_service.is_admin() or not spoc_email:
                return tuple([gr.update()] * 5 + ['<div class="notification" style="background: #ef4444 !important;">❌ Please select a SPOC</div>'])
            
            try:
                success = user_management.update_user_role(spoc_email, USER_ROLES['user'])
                if success:
                    # Refresh all dropdowns with clean formatting
                    user_choices = user_management.get_dropdown_choices_by_role('user')
                    spoc_choices = user_management.get_dropdown_choices_by_role('spoc')
                    admin_choices = user_management.get_dropdown_choices_by_role('admin')
                    
                    notification = '<div class="notification" style="background: #10b981 !important;">✅ SPOC demoted to user successfully</div>'
                    
                    return (
                        gr.update(choices=user_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        gr.update(choices=admin_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        notification
                    )
                else:
                    notification = '<div class="notification" style="background: #ef4444 !important;">❌ Failed to demote SPOC</div>'
                    return tuple([gr.update()] * 5 + [notification])
            except Exception as e:
                notification = f'<div class="notification" style="background: #ef4444 !important;">❌ Error: {str(e)}</div>'
                return tuple([gr.update()] * 5 + [notification])

        def on_transfer_user_selected(user_email):
            """Show current SPOC and update target SPOC dropdown when user is selected"""
            if not user_email:
                return gr.update(visible=False), gr.update()
            
            try:
                # Get current SPOC for this user
                all_assignments = user_management.get_all_spoc_assignments()
                current_spoc = None
                
                for spoc_email, assigned_users in all_assignments.items():
                    if user_email in assigned_users:
                        current_spoc = spoc_email
                        break
                
                if current_spoc:
                    # Get all SPOCs except current one
                    all_spocs = user_management.get_users_by_role_simple('spoc')
                    other_spocs = [s for s in all_spocs if s['email'] != current_spoc]
                    target_choices = [(user_management.format_user_for_dropdown(s), s['email']) for s in other_spocs]
                    
                    # Format current SPOC name
                    spoc_user = next((s for s in all_spocs if s['email'] == current_spoc), None)
                    if spoc_user:
                        current_spoc_name = user_management.format_user_for_dropdown(spoc_user)
                    else:
                        current_spoc_name = current_spoc
                    
                    return gr.update(value=current_spoc_name, visible=True), gr.update(choices=target_choices, value=None)
                else:
                    # No current SPOC
                    all_spocs = user_management.get_users_by_role_simple('spoc')
                    target_choices = [(user_management.format_user_for_dropdown(s), s['email']) for s in all_spocs]
                    return gr.update(value="No SPOC assigned", visible=True), gr.update(choices=target_choices, value=None)
                    
            except Exception as e:
                print(f"Error getting current SPOC: {e}")
                return gr.update(visible=False), gr.update()
        
        def transfer_user_handler(user_email, target_spoc_email):
            """Transfer user to another SPOC"""
            if not ui_service.is_admin() or not user_email or not target_spoc_email:
                return '<div class="notification" style="background: #ef4444 !important;">❌ Please select both user and target SPOC</div>'
            
            try:
                # Remove old assignment and create new one
                user_management.remove_all_spoc_assignments_for_user(user_email)
                success = user_management.add_spoc_assignment(target_spoc_email, user_email)
                
                if success:
                    notification = '<div class="notification" style="background: #10b981 !important;">✅ User transferred successfully</div>'
                    return notification
                else:
                    notification = '<div class="notification" style="background: #ef4444 !important;">❌ Failed to transfer user</div>'
                    return notification
            except Exception as e:
                notification = f'<div class="notification" style="background: #ef4444 !important;">❌ Error: {str(e)}</div>'
                return notification

        def promote_spoc_to_admin_handler(spoc_email):
            """Promote SPOC to admin"""
            if not ui_service.is_admin() or not spoc_email:
                return tuple([gr.update()] * 5 + ['<div class="notification" style="background: #ef4444 !important;">❌ Please select a SPOC</div>'])
            
            try:
                success = user_management.update_user_role(spoc_email, USER_ROLES['admin'])
                if success:
                    # Refresh all dropdowns with clean formatting
                    user_choices = user_management.get_dropdown_choices_by_role('user')
                    spoc_choices = user_management.get_dropdown_choices_by_role('spoc')
                    admin_choices = user_management.get_dropdown_choices_by_role('admin')
                    
                    notification = '<div class="notification" style="background: #10b981 !important;">✅ SPOC promoted to admin successfully</div>'
                    
                    return (
                        gr.update(choices=user_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        gr.update(choices=admin_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        notification
                    )
                else:
                    notification = '<div class="notification" style="background: #ef4444 !important;">❌ Failed to promote SPOC</div>'
                    return tuple([gr.update()] * 5 + [notification])
            except Exception as e:
                notification = f'<div class="notification" style="background: #ef4444 !important;">❌ Error: {str(e)}</div>'
                return tuple([gr.update()] * 5 + [notification])

        def demote_admin_to_spoc_handler(admin_email):
            """Demote admin to SPOC"""
            if not ui_service.is_admin() or not admin_email:
                return tuple([gr.update()] * 5 + ['<div class="notification" style="background: #ef4444 !important;">❌ Please select an admin</div>'])
            
            try:
                success = user_management.update_user_role(admin_email, USER_ROLES['spoc'])
                if success:
                    # Refresh all dropdowns with clean formatting
                    user_choices = user_management.get_dropdown_choices_by_role('user')
                    spoc_choices = user_management.get_dropdown_choices_by_role('spoc')
                    admin_choices = user_management.get_dropdown_choices_by_role('admin')
                    
                    notification = '<div class="notification" style="background: #10b981 !important;">✅ Admin demoted to SPOC successfully</div>'
                    
                    return (
                        gr.update(choices=user_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        gr.update(choices=admin_choices, value=None),
                        gr.update(choices=spoc_choices, value=None),
                        notification
                    )
                else:
                    notification = '<div class="notification" style="background: #ef4444 !important;">❌ Failed to demote admin</div>'
                    return tuple([gr.update()] * 5 + [notification])
            except Exception as e:
                notification = f'<div class="notification" style="background: #ef4444 !important;">❌ Error: {str(e)}</div>'
                return tuple([gr.update()] * 5 + [notification])

        
        # Whitelist management with email validation and SPOC assignment
        
        # Email validation and SPOC visibility
        whitelist_email_input.change(fn=validate_email_input, inputs=[whitelist_email_input], outputs=[email_validation])
        assignment_radio.change(
            fn=lambda assignment: (
                gr.update(visible=(assignment == "Add as User"), value="Select SPOC"),
                gr.update(interactive=(assignment == "Add as User"))
            ),
            inputs=[assignment_radio],
            outputs=[spoc_dropdown, department_input]
        )
        
        # Search functionality
        whitelist_search.change(fn=search_whitelist_data, inputs=[whitelist_search], outputs=[whitelist_table, whitelist_select])
        refresh_whitelist_btn.click(fn=refresh_whitelist_data, outputs=[whitelist_table, whitelist_select])
        
        # Add email with SPOC assignment
        add_to_whitelist_btn.click(
            fn=add_email_to_whitelist_handler,
            inputs=[whitelist_email_input, department_input, assignment_radio, spoc_dropdown],
            outputs=[whitelist_table, whitelist_select, department_input, whitelist_email_input, assignment_radio, spoc_dropdown, whitelist_notification]
        )
        
        # Department management
        add_dept_btn.click(
            fn=add_department_handler,
            inputs=[dept_name_input],
            outputs=[department_input, delete_dept_dropdown, dept_notification]
        )
        
        delete_dept_btn.click(
            fn=delete_department_handler,
            inputs=[delete_dept_dropdown],
            outputs=[department_input, delete_dept_dropdown, dept_notification]
        )

        delete_whitelist_btn.click(
            fn=delete_single_email,
            inputs=[whitelist_select],
            outputs=[whitelist_table, whitelist_select, whitelist_select, whitelist_notification]
        )
                
        # SPOC Assignment tab events
        spoc_filter_dropdown.change(fn=filter_spoc_assignments, inputs=[spoc_filter_dropdown], outputs=[assignments_table])
        refresh_assignments_btn.click(fn=refresh_spoc_assignments, outputs=[assignments_table])
        
        # Role management events
        def refresh_roles_handler():
            """Refresh all role management dropdowns"""
            if not ui_service.is_admin():
                return tuple([gr.update()] * 7 + ['<div class="notification">❌ Admin access required</div>'])
            
            users = user_management.get_all_users()
            regular_users = [u for u in users if u['role'] == 'user']
            spoc_users = [u for u in users if u['role'] == 'spoc']
            admin_users = [u for u in users if u['role'] == 'admin']
            
            user_choices = [(user_management.format_user_for_dropdown(u), u['email']) for u in regular_users]
            spoc_choices = [(user_management.format_user_for_dropdown(u), u['email']) for u in spoc_users]
            admin_choices = [(user_management.format_user_for_dropdown(u), u['email']) for u in admin_users]
            
            assignments_data = user_management.get_assignments_with_names("ALL")
            
            return (
                gr.update(choices=user_choices, value=None),
                gr.update(choices=spoc_choices, value=None),
                gr.update(choices=spoc_choices, value=None),
                gr.update(choices=admin_choices, value=None),
                gr.update(choices=spoc_choices, value=None),
                gr.update(choices=user_choices, value=None),
                gr.update(value=assignments_data),
                '<div class="notification">🔄 Role lists refreshed</div>'
            )
        
        refresh_roles_btn.click(
            fn=refresh_roles_handler,
            outputs=[user_to_spoc_dropdown, spoc_to_user_dropdown, spoc_to_admin_dropdown, admin_to_spoc_dropdown, transfer_to_spoc_dropdown, transfer_user_dropdown, assignments_table, spoc_notification]
        )
        
        user_to_spoc_btn.click(
            fn=promote_user_to_spoc_handler, 
            inputs=[user_to_spoc_dropdown], 
            outputs=[user_to_spoc_dropdown, spoc_to_user_dropdown, spoc_to_admin_dropdown, admin_to_spoc_dropdown, transfer_to_spoc_dropdown, assignments_table, spoc_notification]
        )
        
        spoc_to_user_btn.click(
            fn=demote_spoc_to_user_handler, 
            inputs=[spoc_to_user_dropdown], 
            outputs=[user_to_spoc_dropdown, spoc_to_user_dropdown, spoc_to_admin_dropdown, admin_to_spoc_dropdown, transfer_to_spoc_dropdown, spoc_notification]
        )
        
        spoc_to_admin_btn.click(
            fn=promote_spoc_to_admin_handler, 
            inputs=[spoc_to_admin_dropdown], 
            outputs=[user_to_spoc_dropdown, spoc_to_user_dropdown, spoc_to_admin_dropdown, admin_to_spoc_dropdown, transfer_to_spoc_dropdown, spoc_notification]
        )
        
        admin_to_spoc_btn.click(
            fn=demote_admin_to_spoc_handler, 
            inputs=[admin_to_spoc_dropdown], 
            outputs=[user_to_spoc_dropdown, spoc_to_user_dropdown, spoc_to_admin_dropdown, admin_to_spoc_dropdown, transfer_to_spoc_dropdown, spoc_notification]
        )
        
        transfer_user_dropdown.change(
            fn=on_transfer_user_selected,
            inputs=[transfer_user_dropdown],
            outputs=[current_spoc_display, transfer_to_spoc_dropdown]
        )
        
        transfer_user_btn.click(
            fn=transfer_user_handler, 
            inputs=[transfer_user_dropdown, transfer_to_spoc_dropdown], 
            outputs=[spoc_notification]
        )
        
        # User Hierarchy tab events
        def filter_users_by_role(role_filter):
            """Filter users by role"""
            if not ui_service.is_admin():
                return gr.update()
            
            users_data = user_management.get_users_by_role_table(role_filter)
            return gr.update(value=users_data)
        
        def refresh_user_hierarchy():
            """Refresh user hierarchy table"""
            return filter_users_by_role("All")
        
        role_filter_dropdown.change(fn=filter_users_by_role, inputs=[role_filter_dropdown], outputs=[role_users_table])
        refresh_users_btn.click(fn=refresh_user_hierarchy, outputs=[role_users_table])
        
        # Feedback handlers
        def handle_feedback_submission(feedback_selection, remarks, message_id, history):
            """Handle feedback submission with validation"""
            if not message_id:
                notification = '<div class="notification" style="background: #ef4444 !important;">❌ No message to provide feedback for</div>'
                return (
                    gr.update(interactive=True), 
                    gr.update(visible=False), 
                    history, 
                    "", 
                    None,
                    False, 
                    gr.update(value=notification, visible=True), 
                    gr.update(interactive=True), 
                    gr.update(interactive=True)
                )
            
            if not feedback_selection:
                notification = '<div class="notification" style="background: #f59e0b !important;">⚠️ Please select a rating (Fully/Partially/Nopes)</div>'
                return (
                    gr.update(interactive=True), 
                    gr.update(visible=True), 
                    history, 
                    "", 
                    feedback_selection,
                    True, 
                    gr.update(value=notification, visible=True), 
                    gr.update(interactive=False), 
                    gr.update(interactive=False)
                )
            
            # Extract feedback type (remove emoji)
            if "✅" in feedback_selection:
                feedback_type = "fully"
            elif "⚠️" in feedback_selection:
                feedback_type = "partially"
            elif "❌" in feedback_selection:
                feedback_type = "nopes"
            else:
                feedback_type = feedback_selection.lower()
            
            # MANDATORY validation for partially/nopes
            if feedback_type in ["partially", "nopes"]:
                if not remarks or not remarks.strip():
                    notification = f'<div class="notification" style="background: #f59e0b !important;">⚠️ Feedback remarks are REQUIRED for \'{feedback_type.title()}\' rating</div>'
                    return (
                        gr.update(interactive=True), 
                        gr.update(visible=True), 
                        history, 
                        "", 
                        feedback_selection,
                        True, 
                        gr.update(value=notification, visible=True), 
                        gr.update(interactive=False), 
                        gr.update(interactive=False)
                    )
            
            try:
                # Prepare feedback data
                feedback_data = feedback_type
                if remarks and remarks.strip():
                    feedback_data = f"{feedback_type}:{remarks.strip()}"
                
                # Submit and update history
                updated_history = ui_service.submit_feedback_and_update_history(message_id, feedback_data, history)
                
                success_notification = '<div class="notification">✅ Feedback submitted successfully</div>'
                return (
                    gr.update(interactive=True), 
                    gr.update(visible=False), 
                    updated_history, 
                    "", 
                    None,  # Clear radio selection
                    False, 
                    gr.update(value=success_notification, visible=True), 
                    gr.update(interactive=True), 
                    gr.update(interactive=True)
                )
            
            except Exception as e:
                error_notification = f'<div class="notification" style="background: #ef4444 !important;">❌ Failed to submit feedback: {str(e)}</div>'
                return (
                    gr.update(interactive=True), 
                    gr.update(visible=True), 
                    history, 
                    "", 
                    feedback_selection,
                    True, 
                    gr.update(value=error_notification, visible=True), 
                    gr.update(interactive=False), 
                    gr.update(interactive=False)
                )

        submit_feedback_btn.click(fn=handle_feedback_submission, inputs=[feedback_radio, feedback_remarks, last_assistant_message_id, chatbot], outputs=[chat_input, feedback_row, chatbot, feedback_remarks, feedback_radio, pending_feedback, file_notification, sessions_radio, new_chat_btn])

        def auto_load_latest_or_pending_feedback():
            try:
                conversations = chat_service.get_user_conversations(ui_service.current_user["email"])
                session_choices = [(conv["title"], conv["id"]) for conv in conversations]
                
                if conversations:
                    latest_conv_id = conversations[0]["id"]
                    history, conv_id, _ = ui_service.load_conversation_for_user(latest_conv_id, None)
                    return history, conv_id, gr.update(choices=session_choices, value=conv_id), "", False, None, gr.update(visible=False)
                
                return [], None, gr.update(choices=session_choices, value=None), "", False, None, gr.update(visible=False)
                
            except Exception as e:
                return [], None, gr.update(choices=[], value=None), "", False, None, gr.update(visible=False)
        
        # Logout
        logout_btn.click(fn=lambda: None, js="() => { window.location.href = '/logout'; }")
    
        demo.load(fn=auto_load_latest_or_pending_feedback, outputs=[chatbot, current_conversation_id, sessions_radio, action_status, pending_feedback, pending_feedback_message_id, feedback_row])

    return demo

def create_ui(app: FastAPI):
    """Mount UI to FastAPI app"""
    
    @app.get("/")
    async def landing_page(request: Request):
        user_data = get_logged_in_user(request)
        if not user_data:
            return HTMLResponse(content=create_landing_page_html())
        
        ui_service.set_user(user_data)
        return RedirectResponse("/gradio/")

    @app.get("/chat")
    async def chat_redirect(request: Request):
        return RedirectResponse("/")
    
    @app.middleware("http")
    async def auth_middleware(request, call_next):
        if request.url.path.startswith("/gradio"):
            user_data = get_logged_in_user(request)
            if not user_data:
                return RedirectResponse("/")
            ui_service.set_user(user_data)
        
        response = await call_next(request)
        return response
    
    # Mount Gradio interface
    demo = create_gradio_interface()
    mount_gradio_app(app, demo, path="/gradio")