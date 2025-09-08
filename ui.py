# ui.py - Updated with working User File Manager and auto-refresh assignments
from fastapi import Request, FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
import gradio as gr
from gradio.routes import mount_gradio_app

from auth import get_logged_in_user
from ui_service import ui_service
from config import IS_PRODUCTION, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from supabase import create_client

def create_landing_page_html() -> str:
    """Minimal login page design with document guidelines"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to SEVABOT</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif;
                text-align: center;
                padding: 50px;
                background: white;
                color: #333;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin: 0;
            }
            
            .login-container {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.1);
                padding: 3rem 2.5rem;
                text-align: center;
                max-width: 400px;
                width: 90%;
            }
            
            .namaskaram {
                font-size: 1.1rem;
                color: #333;
                margin-bottom: 0.5rem;
                font-weight: 500;
            }
            
            .title {
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 2.5rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                letter-spacing: 2px;
            }
            
            .login-button {
                display: inline-block;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                border-radius: 8px;
                overflow: hidden;
                margin-bottom: 2rem;
            }
            
            .login-button:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            }
            
            .login-button img {
                border-radius: 8px;
                max-width: 200px;
                height: auto;
            }
            
            .domain-info {
                margin-top: 2rem;
                padding: 1rem;
                background: #f8f9fa;
                border-radius: 12px;
                font-size: 0.9rem;
                color: #6c757d;
                border-left: 4px solid #667eea;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="namaskaram">🙏 Namaskaram, Welcome to</div>
            <h1 class="title">SEVABOT</h1>
            
            <div style="margin: 2rem 0;">
                <a href="/login" class="login-button">
                    <img src="https://developers.google.com/identity/images/btn_google_signin_dark_normal_web.png" 
                         alt="Sign in with Google" />
                </a>
            </div>
            
            <div class="domain-info">
                <strong>Access Restricted:</strong> Only @sadhguru.org email addresses are permitted
            </div>
            
        </div>
    </body>
    </html>
    """

def create_gradio_interface():
    """Create Gradio interface with all improvements"""
    
    with gr.Blocks(
        theme=gr.themes.Soft(), 
        title="SEVABOT",
        head="""
        <style>
        .gradio-container .footer { display: none !important; }
        .gradio-container footer { display: none !important; }
        footer[data-testid="footer"] { display: none !important; }
        .gradio-container > div:last-child { display: none !important; }
        </style>
        """,
        css="""
        .gradio-container, .main, *, html, body, div, span, h1, h2, h3, h4, h5, h6, p, a, button, input, textarea, select, label {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif !important;
        }
        
        .sevabot-logo { 
            font-size: 0 !important;
            height: 60px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            margin: 0 !important;
        }
        
        .sevabot-logo svg {
            width: 220px !important;
            height: 55px !important;
        }
        
        .logout-btn { 
            background-color: #dc2626 !important; 
            color: white !important;
            width: auto !important;
            min-width: 85px !important;
            padding: 8px 16px !important;
            font-size: 14px !important;
        }
        
        .send-btn {
            background-color: #dc2626 !important;
            color: white !important;
            font-weight: 500 !important;
            min-width: 60px !important;
            max-width: 80px !important;
            padding: 8px 16px !important;
            font-size: 14px !important;
        }
        
        .notification {
            position: fixed !important;
            top: 20px !important;
            right: 20px !important;
            background: #10b981 !important;
            color: white !important;
            padding: 12px 20px !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
            z-index: 1000 !important;
            font-weight: 600 !important;
            animation: fadeInOut 3s ease-in-out forwards !important;
        }
        
        @keyframes fadeInOut {
            0% { opacity: 0; transform: translateX(100%); }
            15% { opacity: 1; transform: translateX(0); }
            85% { opacity: 1; transform: translateX(0); }
            100% { opacity: 0; transform: translateX(100%); }
        }
        
        .feedback-btn { 
            min-height: 42px !important; 
            padding: 10px 20px !important; 
            font-size: 14px !important;
            font-weight: 500 !important;
            margin: 5px !important;
            border: 2px solid transparent !important;
        }
        
        .feedback-fully { 
            background-color: rgba(34, 197, 94, 0.15) !important; 
            color: #059669 !important;
            border-color: rgba(34, 197, 94, 0.3) !important;
        }
        .feedback-partially { 
            background-color: rgba(245, 158, 11, 0.15) !important; 
            color: #d97706 !important;
            border-color: rgba(245, 158, 11, 0.3) !important;
        }
        .feedback-nopes { 
            background-color: rgba(239, 68, 68, 0.15) !important; 
            color: #dc2626 !important;
            border-color: rgba(239, 68, 68, 0.3) !important;
        }
        
        .admin-section {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%) !important;
            border: 1px solid rgba(102, 126, 234, 0.2) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            margin-bottom: 20px !important;
        }
        
        .spoc-section {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(251, 191, 36, 0.1) 100%) !important;
            border: 1px solid rgba(245, 158, 11, 0.2) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            margin-bottom: 20px !important;
        }
        
        .copyright-footer {
            text-align: center !important;
            color: #9ca3af !important;
            font-size: 0.875rem !important;
            margin-top: 20px !important;
            padding: 15px !important;
        }
        
        .sessions-list, .chat-interface { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif !important; }
        .tab-nav button { font-size: 1.1em !important; font-weight: 600 !important; padding: 0.6em 1.2em !important; }
        .gradio-container { height: 100vh !important; }
        .main { height: calc(100vh - 80px) !important; overflow-y: auto !important; }
        
        .btn, .btn-primary, .btn-secondary { 
            font-size: 14px !important;
            padding: 8px 16px !important;
            min-height: auto !important;
            width: auto !important;
        }
        
        .block { overflow: visible !important; }
        .panel-wrap { overflow: visible !important; }
        .app { overflow-y: auto !important; height: 100vh !important; }
        """) as demo:
        
        # State variables
        current_conversation_id = gr.State(None)
        last_assistant_message_id = gr.State(None)
        selected_chat_user = gr.State(None)
        selected_user_for_file_manager = gr.State(None)
        
        # Header with user greeting
        with gr.Row():
            with gr.Column(scale=3):
                sevabot_logo = gr.HTML("""
                <div style="display: flex; align-items: center;">
                    <svg width="240" height="55" viewBox="0 0 200 50">
                        <defs>
                            <linearGradient id="headerLogoGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                                <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
                            </linearGradient>
                        </defs>
                        <circle cx="20" cy="25" r="18" fill="none" stroke="url(#headerLogoGradient)" stroke-width="1.5" opacity="0.3"/>
                        <text x="20" y="32" font-size="18" text-anchor="middle" fill="url(#headerLogoGradient)">🙏</text>
                        <text x="50" y="32" font-family="'Google Sans', 'Product Sans', 'Roboto', system-ui, sans-serif" font-size="20" font-weight="600" fill="url(#headerLogoGradient)" letter-spacing="1.8px">SEVABOT</text>
                        <circle cx="160" cy="20" r="2.5" fill="url(#headerLogoGradient)" opacity="0.8"/>
                        <circle cx="170" cy="25" r="2" fill="url(#headerLogoGradient)" opacity="0.6"/>
                        <circle cx="178" cy="30" r="1.8" fill="url(#headerLogoGradient)" opacity="0.7"/>
                    </svg>
                </div>
                """, elem_classes="sevabot-logo")
            with gr.Column(scale=1):
                with gr.Row():
                    namaskaram_user = gr.Button("", variant="secondary", interactive=False, scale=4)
                    logout_btn = gr.Button("Logout", variant="stop", elem_classes="logout-btn", scale=1)
        
        # Main interface with tabs
        with gr.Tabs():
            # Chat Tab (for all users)
            with gr.TabItem("💬 Chat"):
                with gr.Row():
                    # Left sidebar - Sessions
                    with gr.Column(scale=1, min_width=250):
                        gr.Markdown("### Chat Sessions")
                        with gr.Row():
                            new_chat_btn = gr.Button("🆕 New", variant="primary")
                            delete_chat_btn = gr.Button("🗑️ Delete", variant="secondary")
                            refresh_chat_btn = gr.Button("🔄 Refresh", variant="secondary")
                        
                        sessions_radio = gr.Radio(
                            label="Conversations",
                            choices=[],
                            value=None,
                            interactive=True,
                            show_label=False,
                            elem_classes="sessions-list"
                        )
                    
                    # Main content area
                    with gr.Column(scale=4):
                        # Admin/SPOC user selection for chat viewing
                        with gr.Column(visible=False) as admin_chat_user_section:
                            gr.Markdown("#### 👑 Admin/SPOC: View User Chats")
                            
                            with gr.Row():
                                chat_users_dropdown = gr.Dropdown(
                                    label="Select User to View Chats (Including Admins)",
                                    choices=[],
                                    value=None,
                                    interactive=True,
                                    filterable=True,
                                    scale=3
                                )
                                refresh_chat_users_btn = gr.Button("🔄 Refresh Users", variant="secondary", scale=1)
                        
                        # Chat interface (visible to all)
                        chatbot = gr.Chatbot(
                            label="",
                            height="55vh",
                            show_copy_button=True,
                            show_share_button=False,
                            elem_classes="chat-interface"
                        )
                        
                        # Enhanced feedback row
                        with gr.Column(visible=False) as feedback_row:
                            gr.Markdown("**Rate how well the query is answered:**")
                            with gr.Row():
                                feedback_fully = gr.Button("✅ Fully", variant="secondary", elem_classes="feedback-btn feedback-fully")
                                feedback_partially = gr.Button("⚠️ Partially", variant="secondary", elem_classes="feedback-btn feedback-partially")
                                feedback_nopes = gr.Button("❌ Nopes", variant="secondary", elem_classes="feedback-btn feedback-nopes")
                            
                            feedback_remarks = gr.Textbox(
                                label="Additional feedback (optional)",
                                placeholder="Your feedback helps improve responses...",
                                lines=2
                            )
                            
                            feedback_warning = gr.Markdown("", visible=False)
                        
                        # Message input 
                        message_input = gr.Textbox(
                            label="",
                            placeholder="Ask me anything about the knowledge repository...",
                            lines=3,
                            max_lines=6,
                            show_label=False,
                            interactive=True
                        )
                        
                        # Note and send button in same line
                        with gr.Row():
                            gr.Markdown("*Press Shift+Enter to send message, Enter for new line*")
                            send_btn = gr.Button("Send", variant="primary", elem_classes="send-btn")
            
            # Files Tab (for regular users to view common knowledge)
            with gr.TabItem("📄 Files", visible=False) as files_tab:
                gr.Markdown("## 📚 Knowledge Repository")
                gr.Markdown("*Browse the documents available in our knowledge repository*")
                
                with gr.Row():
                    refresh_files_btn = gr.Button("🔄 Refresh", variant="secondary")
                
                user_files_table = gr.Dataframe(
                    label="Available Documents",
                    headers=["Document Name", "Size", "Type", "Added Date"],
                    datatype=["str", "str", "str", "str"],
                    interactive=False,
                    wrap=True
                )
            
            # File Manager (Common) Tab (for admins and SPOCs)
            with gr.TabItem("📂 File Manager (Common)", visible=False) as file_manager_tab:
                with gr.Column() as file_manager_container:
                    file_manager_title = gr.Markdown("## 📚 Common Knowledge Repository")
                    
                    # Document Guidelines
                    file_manager_guidelines = gr.Markdown("""
                    **📋 Common Knowledge Repository:**
                    • Max file size: 10MB | Supported formats: .txt, .md, .pdf, .docx | PDFs must be text-extractable (OCR not supported)
                    • Files are uploaded to the common knowledge repository and available to all users
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
                    
                    # File list with search (for both admin and SPOC)
                    gr.Markdown("### 📋 Documents in Knowledge Repository")
                    
                    # Search box for files
                    file_search_box = gr.Textbox(
                        label="Search Files",
                        placeholder="Type to search files by name, type, or status...",
                        interactive=True
                    )
                    
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 Refresh")
                        reindex_btn = gr.Button("🔍 Re-index", variant="primary", visible=False)  # Admin only
                        cleanup_btn = gr.Button("🧹 Cleanup", variant="secondary", visible=False)  # Admin only
                        vector_stats_btn = gr.Button("📊 Vector Stats", variant="secondary")
                    
                    files_table = gr.Dataframe(
                        label="",
                        headers=["File Name", "Size", "Type", "Chunks", "Status", "Uploaded", "Uploaded By"],
                        datatype=["str", "str", "str", "number", "str", "str", "str"],
                        interactive=False,
                        wrap=True
                    )
                    
                    # Status displays
                    upload_status = gr.Textbox(label="Upload Progress", visible=False, lines=6)
                    delete_status = gr.Textbox(label="Delete Progress", visible=False, lines=6)
                    vector_status = gr.Markdown(label="Vector Database Status", visible=False)
            
            # File Manager (Users) Tab (for admins only) - FIXED IMPLEMENTATION
            with gr.TabItem("👥 File Manager (Users)", visible=False) as user_file_manager_tab:
                with gr.Column(elem_classes="admin-section"):
                    gr.Markdown("## 👑 Admin User File Management")
                    gr.Markdown("*This feature allows viewing user documents but individual upload is not yet implemented*")
                    
                    with gr.Row():
                        user_file_users_dropdown = gr.Dropdown(
                            label="Select User",
                            choices=[],
                            value=None,
                            interactive=True,
                            filterable=True,
                            scale=3
                        )
                        refresh_user_file_users_btn = gr.Button("🔄 Refresh Users", variant="secondary", scale=1)
                    
                    user_file_selected_user_info = gr.Markdown("*No user selected*")
                    
                    # FIXED: Note about current implementation
                    gr.Markdown("""
                    **📋 Current Status:**
                    • This application uses a common knowledge repository shared by all users
                    • Individual per-user file management is not currently implemented  
                    • All users access the same document collection from the Common Knowledge Repository
                    • Use the "File Manager (Common)" tab to manage documents available to all users
                    """)
                    
                    # Placeholder user file management sections (disabled)
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 📤 Upload Documents for User (Not Implemented)")
                            user_file_upload = gr.File(
                                label="Select files (disabled)",
                                file_types=[".txt", ".md", ".pdf", ".docx"],
                                file_count="multiple",
                                type="filepath",
                                interactive=False
                            )
                            user_upload_btn = gr.Button("📤 Upload Files", variant="primary", interactive=False)
                        
                        with gr.Column():
                            gr.Markdown("### 🗑️ Delete User Documents (Not Implemented)")
                            user_selected_files = gr.CheckboxGroup(
                                label="Select files (disabled)",
                                choices=[],
                                value=[],
                                interactive=False
                            )
                            with gr.Row():
                                user_delete_btn = gr.Button("🗑️ Delete Selected", variant="secondary", interactive=False)
                                user_select_all_btn = gr.Button("☑️ Select All", variant="secondary", interactive=False)
                    
                    gr.Markdown("### 📋 User Documents (Shows Common Knowledge)")
                    
                    user_file_search_box = gr.Textbox(
                        label="Search Files",
                        placeholder="Shows common knowledge documents...",
                        interactive=False
                    )
                    
                    with gr.Row():
                        user_refresh_btn = gr.Button("🔄 Refresh", variant="secondary")
                        user_reindex_btn = gr.Button("🔍 Re-index", variant="primary", interactive=False)
                        user_cleanup_btn = gr.Button("🧹 Cleanup", variant="secondary", interactive=False)
                        user_vector_stats_btn = gr.Button("📊 Vector Stats", variant="secondary")
                    
                    user_files_table = gr.Dataframe(
                        label="Common Knowledge Documents (Shared by All Users)",
                        headers=["File Name", "Size", "Type", "Chunks", "Status", "Uploaded", "Uploaded By"],
                        datatype=["str", "str", "str", "number", "str", "str", "str"],
                        interactive=False,
                        wrap=True
                    )
                    
                    # Status displays for user file management
                    user_upload_status = gr.Textbox(label="Status", visible=False, lines=6)
                    user_delete_status = gr.Textbox(label="Status", visible=False, lines=6)
                    user_vector_status = gr.Markdown(label="Vector Database Status", visible=False)
            
            # Users Tab (for admins only - SPOC management) - FIXED AUTO-REFRESH
            with gr.TabItem("👥 Users", visible=False) as users_tab:
                with gr.Column(elem_classes="admin-section"):
                    gr.Markdown("## 👑 Admin User Management - SPOC Assignments")
                    gr.Markdown("*Manage SPOC (Single Point of Contact) assignments to control chat visibility*")
                    
                    # FIXED: Added refresh button for assignments overview
                    with gr.Row():
                        gr.Markdown("### 📋 All SPOC Assignments Overview")
                        refresh_assignments_btn = gr.Button("🔄 Refresh Assignments", variant="secondary")
                    
                    assignments_table = gr.Dataframe(
                        label="",
                        headers=["SPOC Email", "SPOC Name", "Assigned User", "User Name", "Assignment Date"],
                        datatype=["str", "str", "str", "str", "str"],
                        interactive=False,
                        wrap=True
                    )
                    
                    # SPOC Role Management Section
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 🔧 Manage SPOC Roles")
                            
                            role_management_dropdown = gr.Dropdown(
                                label="Select User",
                                choices=[],
                                value=None,
                                interactive=True,
                                filterable=True
                            )
                            
                            with gr.Row():
                                promote_to_spoc_btn = gr.Button("⬆️ Promote to SPOC", variant="primary")
                                demote_to_user_btn = gr.Button("⬇️ Demote to User", variant="secondary")
                        
                        with gr.Column():
                            gr.Markdown("### ℹ️ Current Roles")
                            current_roles_display = gr.Markdown(
                                value="Loading roles..."
                            )
                    
                    with gr.Row():
                        # SPOC Assignment Section
                        with gr.Column():
                            gr.Markdown("### Add SPOC Assignment")
                            
                            spoc_email_dropdown = gr.Dropdown(
                                label="Select SPOC",
                                choices=[],
                                value=None,
                                interactive=True,
                                filterable=True
                            )
                            
                            user_email_dropdown = gr.Dropdown(
                                label="Select User to Assign",
                                choices=[],
                                value=None,
                                interactive=True,
                                filterable=True
                            )
                            
                            with gr.Row():
                                add_assignment_btn = gr.Button("➕ Add Assignment", variant="primary")
                                refresh_users_btn = gr.Button("🔄 Refresh Users", variant="secondary")
                        
                        # Current Assignments Section
                        with gr.Column():
                            gr.Markdown("### Current SPOC Assignments")
                            
                            current_spoc_dropdown = gr.Dropdown(
                                label="View Assignments for SPOC",
                                choices=[],
                                value=None,
                                interactive=True
                            )
                            
                            assigned_users_list = gr.CheckboxGroup(
                                label="Assigned Users",
                                choices=[],
                                value=[]
                            )
                            
                            remove_assignment_btn = gr.Button("➖ Remove Selected", variant="secondary")
                    
                    # Status display
                    assignment_status = gr.Textbox(label="Status", visible=False, lines=3)
        
        # Copyright footer
        gr.HTML("""
        <div class="copyright-footer">
            <p>© Sadhguru, 2025 | This AI chat may make mistakes. Please use with discretion.</p>
        </div>
        """)
        
        # Hidden components
        action_status = gr.Textbox(visible=False)
        file_notification = gr.HTML("", visible=False)
        
        # Load initial data and set visibility based on roles
        def load_initial_data():
            user_name = ui_service.get_display_name()
            user_role = ui_service.get_user_role()
            user_email = ui_service.current_user.get("email", "")
            
            # User greeting based on role
            if user_role == "admin":
                greeting = f"Namaskaram {user_name}! [ADMIN]"
            elif user_role == "spoc":
                greeting = f"Namaskaram {user_name}! [SPOC]"
            else:
                greeting = f"Namaskaram {user_name}!"
            
            sessions_update = ui_service.load_initial_data()[1]
            
            # Visibility based on role
            files_tab_visible = user_role == "user"
            file_manager_visible = user_role in ["admin", "spoc"]
            user_file_manager_visible = user_role == "admin"
            users_tab_visible = user_role == "admin"
            
            # File manager section visibility
            admin_chat_section_visible = user_role in ["admin", "spoc"]
            admin_upload_section_visible = user_role == "admin"
            reindex_visible = user_role == "admin"
            cleanup_visible = user_role == "admin"
            
            # Auto-select current user for admin/SPOC chat view
            default_chat_user = user_email if user_role in ["admin", "spoc"] else None
            
            # Update titles and guidelines based on role
            if user_role == "spoc":
                title_text = "## 📋 SPOC File Management - Common Knowledge Repository"
                guidelines_text = """
                **📋 Common Knowledge Repository:**
                • Browse and manage documents in the common knowledge repository
                • Files are available to all users for queries
                • Contact administrators for file uploads and deletions
                """
                container_class = "spoc-section"
            else:
                title_text = "## 📚 Common Knowledge Repository"
                guidelines_text = """
                **📋 Common Knowledge Repository:**
                • Max file size: 10MB | Supported formats: .txt, .md, .pdf, .docx | PDFs must be text-extractable (OCR not supported)
                • Files are uploaded to the common knowledge repository and available to all users
                """
                container_class = "admin-section"
            
            return (
                greeting,
                sessions_update,
                gr.update(visible=files_tab_visible),
                gr.update(visible=file_manager_visible),
                gr.update(visible=user_file_manager_visible),
                gr.update(visible=users_tab_visible),
                gr.update(visible=admin_chat_section_visible),
                gr.update(visible=admin_upload_section_visible),
                gr.update(visible=reindex_visible),
                gr.update(visible=cleanup_visible),
                gr.update(value=title_text),
                gr.update(value=guidelines_text),
                gr.update(elem_classes=container_class),
                gr.update(value=default_chat_user)
            )
        
        demo.load(
            fn=load_initial_data, 
            outputs=[
                namaskaram_user, 
                sessions_radio,
                files_tab,
                file_manager_tab,
                user_file_manager_tab,
                users_tab,
                admin_chat_user_section,
                admin_upload_section,
                reindex_btn,
                cleanup_btn,
                file_manager_title,
                file_manager_guidelines,
                file_manager_container,
                chat_users_dropdown
            ]
        )
        
        # Load files for regular users
        def load_user_files():
            if ui_service.get_user_role() == "user":
                files = ui_service.get_common_knowledge_file_list_for_users()
                return gr.update(value=files)
            return gr.update(value=[])
        
        demo.load(fn=load_user_files, outputs=[user_files_table])
        
        # Load admin data with role management
        def load_admin_data():
            if ui_service.is_admin():
                files = ui_service.get_common_knowledge_file_list()
                choices = [row[0] for row in files] if files else []
                
                # Load users for SPOC management
                users = ui_service.get_all_users_for_admin()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                regular_users = [user for user in users if user['role'] == 'user']
                all_users_for_chat = [user for user in users if user['role'] in ['user', 'spoc', 'admin']]
                
                # All users for role management
                all_user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                
                spoc_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in spoc_users]
                user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in regular_users]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in all_users_for_chat]
                
                # User file manager choices (all users)
                user_file_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in users]
                
                # Create role summary - Using proper markdown formatting
                role_summary = f"**Current User Roles:**\n\n"
                role_summary += f"• Admins: {len([u for u in users if u['role'] == 'admin'])}\n"
                role_summary += f"• SPOCs: {len(spoc_users)}\n"
                role_summary += f"• Users: {len(regular_users)}\n\n"
                
                if spoc_users:
                    role_summary += "**SPOC Users:**\n"
                    for spoc in spoc_users:
                        role_summary += f"• {spoc['name']} ({spoc['email']})\n"
                
                return (
                    gr.update(value=files),
                    gr.update(choices=choices, value=[]),
                    gr.update(choices=all_user_choices),
                    gr.update(value=role_summary),
                    gr.update(choices=spoc_choices),
                    gr.update(choices=user_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(choices=chat_user_choices),
                    gr.update(choices=user_file_choices)
                )
            elif ui_service.is_spoc():
                files = ui_service.get_common_knowledge_file_list()
                
                # SPOCs can see assigned users for chat
                assigned_users = ui_service.get_assigned_users_for_spoc()
                users = ui_service.get_all_users_for_admin()
                
                # Filter to only assigned users
                assigned_user_details = [user for user in users if user['email'] in assigned_users]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in assigned_user_details]
                
                return (
                    gr.update(value=files),
                    gr.update(choices=[], value=[]),
                    gr.update(choices=[]),
                    gr.update(value=""),
                    gr.update(choices=[]),
                    gr.update(choices=[]),
                    gr.update(choices=[]),
                    gr.update(choices=chat_user_choices),
                    gr.update(choices=[])
                )
            
            return (
                gr.update(value=[]),
                gr.update(choices=[], value=[]),
                gr.update(choices=[]),
                gr.update(value=""),
                gr.update(choices=[]),
                gr.update(choices=[]),
                gr.update(choices=[]),
                gr.update(choices=[]),
                gr.update(choices=[])
            )
        
        demo.load(
            fn=load_admin_data,
            outputs=[
                files_table,
                selected_files,
                role_management_dropdown,
                current_roles_display,
                spoc_email_dropdown,
                user_email_dropdown,
                current_spoc_dropdown,
                chat_users_dropdown,
                user_file_users_dropdown
            ]
        )
        
        # Load assignments overview table
        def load_assignments_overview():
            if ui_service.is_admin():
                try:
                    # Get all SPOC assignments
                    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                    assignments_result = supabase.table("spoc_assignments")\
                        .select("*")\
                        .order("created_at", desc=True)\
                        .execute()
                    
                    if not assignments_result.data:
                        return gr.update(value=[])
                    
                    # Get user details for names
                    users = ui_service.get_all_users_for_admin()
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
                    
                    return gr.update(value=assignments_data)
                except Exception as e:
                    print(f"Error loading assignments overview: {e}")
                    return gr.update(value=[])
            
            return gr.update(value=[])
        
        demo.load(fn=load_assignments_overview, outputs=[assignments_table])
        
        # FIXED: Auto-load current user's conversations on initial load
        def auto_load_user_conversations():
            """Auto-load current user's conversations when they log in"""
            if ui_service.is_admin_or_spoc():
                # Auto-select current user and load their conversations
                user_email = ui_service.current_user.get("email", "")
                if user_email:
                    conversations = ui_service.get_user_conversations_for_admin(user_email)
                    session_choices = [(conv["title"], conv["id"]) for conv in conversations]
                    return gr.update(choices=session_choices, value=None)
            return gr.update()
        
        # Trigger when chat user is auto-selected
        demo.load(fn=auto_load_user_conversations, outputs=[sessions_radio])
        
        # Chat user selection for admin/SPOC
        def select_user_for_chat(selected_user_email):
            if not ui_service.is_admin_or_spoc() or not selected_user_email:
                return gr.update()
            
            conversations = ui_service.get_user_conversations_for_admin(selected_user_email)
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            
            return gr.update(choices=session_choices, value=None)
        
        def refresh_chat_users():
            if ui_service.is_admin():
                users = ui_service.get_all_users_for_admin()
                all_users_for_chat = [user for user in users if user['role'] in ['user', 'spoc', 'admin']]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in all_users_for_chat]
                return gr.update(choices=chat_user_choices)
            elif ui_service.is_spoc():
                assigned_users = ui_service.get_assigned_users_for_spoc()
                users = ui_service.get_all_users_for_admin()
                assigned_user_details = [user for user in users if user['email'] in assigned_users]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in assigned_user_details]
                return gr.update(choices=chat_user_choices)
            
            return gr.update(choices=[])
        
        def refresh_current_user_chats():
            """Refresh current user's own chats"""
            conversations = ui_service.get_user_conversations_for_admin(ui_service.current_user["email"])
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            return gr.update(choices=session_choices, value=None)
        
        # Bind chat user events
        chat_users_dropdown.change(
            fn=select_user_for_chat,
            inputs=[chat_users_dropdown],
            outputs=[sessions_radio]
        ).then(
            fn=lambda email: email,
            inputs=[chat_users_dropdown],
            outputs=[selected_chat_user]
        )
        
        refresh_chat_users_btn.click(
            fn=refresh_chat_users,
            outputs=[chat_users_dropdown]
        )
        
        refresh_chat_btn.click(
            fn=refresh_current_user_chats,
            outputs=[sessions_radio]
        )
        
        # Chat message handling
        def handle_send_message(message, history, conv_id):
            if not message.strip():
                return history, "", conv_id, gr.update(), "", gr.update(interactive=True), gr.update(visible=False), None
            
            new_history, empty_msg, new_conv_id, sessions_update, status = ui_service.send_message(message, history, conv_id)
            assistant_msg_id = ui_service.get_last_assistant_message_id()
            
            return new_history, empty_msg, new_conv_id, sessions_update, status, gr.update(interactive=False), gr.update(visible=True), assistant_msg_id
        
        # Bind both message input submit and send button
        message_input.submit(
            fn=handle_send_message,
            inputs=[message_input, chatbot, current_conversation_id],
            outputs=[chatbot, message_input, current_conversation_id, sessions_radio, action_status, message_input, feedback_row, last_assistant_message_id]
        )
        
        send_btn.click(
            fn=handle_send_message,
            inputs=[message_input, chatbot, current_conversation_id],
            outputs=[chatbot, message_input, current_conversation_id, sessions_radio, action_status, message_input, feedback_row, last_assistant_message_id]
        )
        
        # Enhanced feedback handlers
        def handle_feedback(feedback_type, message_id, remarks, history):
            if not message_id:
                return gr.update(interactive=True), gr.update(visible=False), history, "", gr.update(visible=False)
                
            if feedback_type in ["partially", "nopes"] and (not remarks or not remarks.strip()):
                warning_msg = f"Warning: Please provide feedback remarks for '{feedback_type.title()}' rating."
                return gr.update(interactive=True), gr.update(visible=True), history, "", gr.update(value=warning_msg, visible=True)
            
            try:
                feedback_data = feedback_type
                if remarks and remarks.strip():
                    feedback_data = f"{feedback_type}:{remarks.strip()}"
                
                ui_service.submit_feedback(message_id, feedback_data)
                
                if history and len(history) > 0:
                    last_exchange = history[-1]
                    if len(last_exchange) >= 2:
                        feedback_emoji = {"fully": "✅", "partially": "⚠️", "nopes": "❌"}[feedback_type]
                        feedback_display = f"{feedback_emoji} {feedback_type.title()}"
                        if remarks and remarks.strip():
                            feedback_display += f" - {remarks.strip()}"
                        
                        updated_response = last_exchange[1] + f"\n\n*[Feedback: {feedback_display}]*"
                        history[-1] = [last_exchange[0], updated_response]
                
                return gr.update(interactive=True), gr.update(visible=False), history, "", gr.update(visible=False)
        
            except Exception as e:
                error_msg = f"Error: Failed to submit feedback: {str(e)}"
                return gr.update(interactive=True), gr.update(visible=True), history, "", gr.update(value=error_msg, visible=True)

        # Bind feedback buttons
        feedback_fully.click(
            fn=lambda msg_id, remarks, hist: handle_feedback("fully", msg_id, remarks, hist),
            inputs=[last_assistant_message_id, feedback_remarks, chatbot],
            outputs=[message_input, feedback_row, chatbot, feedback_remarks, feedback_warning]
        )
        
        feedback_partially.click(
            fn=lambda msg_id, remarks, hist: handle_feedback("partially", msg_id, remarks, hist),
            inputs=[last_assistant_message_id, feedback_remarks, chatbot],
            outputs=[message_input, feedback_row, chatbot, feedback_remarks, feedback_warning]
        )
        
        feedback_nopes.click(
            fn=lambda msg_id, remarks, hist: handle_feedback("nopes", msg_id, remarks, hist),
            inputs=[last_assistant_message_id, feedback_remarks, chatbot],
            outputs=[message_input, feedback_row, chatbot, feedback_remarks, feedback_warning]
        )
        
        # Session management
        def handle_new_chat():
            try:
                initial_history, conv_id, sessions_update, status = ui_service.create_new_chat()
                return initial_history, conv_id, sessions_update, status
            except Exception as e:
                return [], None, gr.update(), "Error creating new chat"
        
        new_chat_btn.click(fn=handle_new_chat, outputs=[chatbot, current_conversation_id, sessions_radio, action_status])
        
        sessions_radio.change(
            fn=ui_service.load_conversation,
            inputs=[sessions_radio],
            outputs=[chatbot, current_conversation_id, action_status]
        )
        
        delete_chat_btn.click(
            fn=ui_service.delete_conversation,
            inputs=[sessions_radio],
            outputs=[chatbot, current_conversation_id, sessions_radio, action_status]
        )
        
        # File search functionality for common knowledge
        def handle_file_search(search_term):
            if ui_service.is_admin_or_spoc():
                files = ui_service.get_common_knowledge_file_list(search_term)
                choices = [row[0] for row in files] if files else []
                return gr.update(value=files), gr.update(choices=choices, value=[])
            return gr.update(), gr.update()
        
        file_search_box.change(
            fn=handle_file_search,
            inputs=[file_search_box],
            outputs=[files_table, selected_files]
        )
        
        # File operations for common knowledge (upload/delete only for admins)
        def handle_upload_complete(files):
            if ui_service.is_admin():
                files_update, status, choices_update = ui_service.upload_files_to_common_knowledge(files)
                success_count = status.count("✅")
                notification = f'<div class="notification">📤 Upload Complete: {success_count} files processed</div>'
                
                enhanced_files = ui_service.get_common_knowledge_file_list()
                admin_choices = [row[0] for row in enhanced_files] if enhanced_files else []
                
                return gr.update(value=enhanced_files), gr.update(value=status, visible=True), gr.update(choices=admin_choices, value=[]), gr.update(value=notification, visible=True)
            else:
                return gr.update(), gr.update(value="Access denied - Admin only", visible=True), gr.update(), gr.update(value='<div class="notification">❌ Access denied</div>', visible=True)

        upload_btn.click(
            fn=handle_upload_complete, 
            inputs=[file_upload], 
            outputs=[files_table, upload_status, selected_files, file_notification]
        )
        
        def handle_delete_complete(selected):
            if ui_service.is_admin():
                files_update, status, choices_update = ui_service.delete_common_knowledge_files_with_progress(selected)
                success_count = status.count("✅")
                notification = f'<div class="notification">🗑️ Deletion Complete: {success_count} files removed</div>'
                
                enhanced_files = ui_service.get_common_knowledge_file_list()
                admin_choices = [row[0] for row in enhanced_files] if enhanced_files else []
                
                return gr.update(value=enhanced_files), gr.update(value=status, visible=True), gr.update(choices=admin_choices, value=[]), gr.update(value=notification, visible=True)
            else:
                return gr.update(), gr.update(value="Access denied - Admin only", visible=True), gr.update(), gr.update(value='<div class="notification">❌ Access denied</div>', visible=True)
        
        delete_btn.click(
            fn=handle_delete_complete, 
            inputs=[selected_files], 
            outputs=[files_table, delete_status, selected_files, file_notification]
        )
        
        def select_all_files():
            if ui_service.is_admin_or_spoc():
                files = ui_service.get_common_knowledge_file_list()
                all_files = [row[0] for row in files] if files else []
                return gr.update(value=all_files)
            return gr.update(value=[])
        
        select_all_btn.click(fn=select_all_files, outputs=[selected_files])
        
        # Regular user file refresh
        def handle_refresh_user_files():
            files = ui_service.get_common_knowledge_file_list_for_users()
            notification = '<div class="notification">🔄 Files refreshed</div>'
            return gr.update(value=files), gr.update(value=notification, visible=True)
        
        refresh_files_btn.click(
            fn=handle_refresh_user_files,
            outputs=[user_files_table, file_notification]
        )
        
        # Common knowledge file management
        def handle_refresh_with_notification(search_term=""):
            if ui_service.is_admin_or_spoc():
                files = ui_service.get_common_knowledge_file_list(search_term)
                choices = [row[0] for row in files] if files else []
                notification = f'<div class="notification">🔄 Files refreshed</div>'
                return gr.update(value=files), gr.update(choices=choices, value=[]), gr.update(value=notification, visible=True)
            else:
                return gr.update(), gr.update(), gr.update(value='<div class="notification">❌ Access denied</div>', visible=True)
        
        refresh_btn.click(
            fn=lambda: handle_refresh_with_notification(),
            outputs=[files_table, selected_files, file_notification]
        )
        
        def handle_reindex_with_notification():
            if ui_service.is_admin():
                result = ui_service.reindex_common_knowledge_pending_files()
                files = ui_service.get_common_knowledge_file_list()
                choices = [row[0] for row in files] if files else []
                notification = f'<div class="notification">🔍 Re-indexing Complete</div>'
                return gr.update(value=files), gr.update(choices=choices), result, gr.update(value=notification, visible=True)
            else:
                return gr.update(), gr.update(), "Access denied - Admin only", gr.update(value='<div class="notification">❌ Access denied</div>', visible=True)
        
        reindex_btn.click(
            fn=handle_reindex_with_notification,
            outputs=[files_table, selected_files, action_status, file_notification]
        )
        
        def handle_cleanup_with_notification():
            if ui_service.is_admin():
                result = ui_service.cleanup_common_knowledge_vector_database()
                files = ui_service.get_common_knowledge_file_list()
                choices = [row[0] for row in files] if files else []
                notification = f'<div class="notification">🧹 Cleanup Complete</div>'
                return result, gr.update(value=files), gr.update(choices=choices, value=[]), gr.update(value=notification, visible=True)
            else:
                return "Access denied - Admin only", gr.update(), gr.update(), gr.update(value='<div class="notification">❌ Access denied</div>', visible=True)
        
        cleanup_btn.click(
            fn=handle_cleanup_with_notification,
            outputs=[action_status, files_table, selected_files, file_notification]
        )
        
        # Vector stats (available to both admin and SPOC)
        def get_vector_stats():
            if ui_service.is_admin_or_spoc():
                stats = "📊 **Common Knowledge Repository Statistics**\n\n"
                try:
                    files = ui_service.get_common_knowledge_file_list()
                    total_files = len(files)
                    indexed_files = len([f for f in files if f[4] == "✅ Indexed"])  # Status is at index 4
                    
                    stats += f"• Total files: {total_files}\n"
                    stats += f"• Indexed files: {indexed_files}\n"
                    stats += f"• Pending files: {total_files - indexed_files}\n"
                    
                    if total_files > 0:
                        stats += f"• Index completion: {(indexed_files/total_files)*100:.1f}%"
                    
                except Exception as e:
                    stats += f"Error getting stats: {str(e)}"
                
                return gr.update(value=stats, visible=True)
            else:
                return gr.update(value="Access denied", visible=True)
        
        vector_stats_btn.click(fn=get_vector_stats, outputs=[vector_status])
        
        # FIXED: User File Manager functionality - Show common knowledge files
        def refresh_user_file_manager():
            """Show common knowledge files for user file manager (since we use shared repository)"""
            if ui_service.is_admin():
                files = ui_service.get_common_knowledge_file_list()
                notification = '<div class="notification">🔄 Showing common knowledge files (shared by all users)</div>'
                return gr.update(value=files), gr.update(value=notification, visible=True)
            return gr.update(), gr.update(value="Access denied", visible=True)
        
        def refresh_user_file_users():
            """Refresh user list for file manager"""
            if ui_service.is_admin():
                users = ui_service.get_all_users_for_admin()
                user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in users]
                return gr.update(choices=user_choices)
            return gr.update(choices=[])
        
        def select_user_for_file_manager(user_email):
            """Select user and show info"""
            if ui_service.is_admin() and user_email:
                users = ui_service.get_all_users_for_admin()
                user_info = next((u for u in users if u['email'] == user_email), None)
                if user_info:
                    info_text = f"**Selected User:** {user_info['name']} ({user_info['email']})\n"
                    info_text += f"**Role:** {user_info['role'].upper()}\n"
                    info_text += f"**Note:** Currently showing common knowledge repository (shared by all users)"
                    return gr.update(value=info_text)
            return gr.update(value="*No user selected*")
        
        def user_file_vector_stats():
            """Show vector stats for user file manager"""
            return get_vector_stats()  # Same as common knowledge stats
        
        # Bind user file manager events
        refresh_user_file_users_btn.click(
            fn=refresh_user_file_users,
            outputs=[user_file_users_dropdown]
        )
        
        user_file_users_dropdown.change(
            fn=select_user_for_file_manager,
            inputs=[user_file_users_dropdown],
            outputs=[user_file_selected_user_info]
        )
        
        user_refresh_btn.click(
            fn=refresh_user_file_manager,
            outputs=[user_files_table, user_upload_status]
        )
        
        user_vector_stats_btn.click(
            fn=user_file_vector_stats,
            outputs=[user_vector_status]
        )
        
        # Role management functions - FIXED: Auto-refresh assignments table
        def promote_user_to_spoc_handler(user_email):
            if not ui_service.is_admin() or not user_email:
                return gr.update(value="Please select a user", visible=True), gr.update(), gr.update(), gr.update(), gr.update()
            
            success = ui_service.promote_user_to_spoc(user_email)
            if success:
                # Refresh dropdowns
                users = ui_service.get_all_users_for_admin()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                spoc_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in spoc_users]
                
                # Update role summary
                role_summary = "**Current User Roles:**\n\n"
                role_summary += f"• Admins: {len([u for u in users if u['role'] == 'admin'])}\n"
                role_summary += f"• SPOCs: {len(spoc_users)}\n"
                role_summary += f"• Users: {len([u for u in users if u['role'] == 'user'])}\n\n"
                
                if spoc_users:
                    role_summary += "**SPOC Users:**\n"
                    for spoc in spoc_users:
                        role_summary += f"• {spoc['name']} ({spoc['email']})\n"
                
                # FIXED: Refresh assignments table
                assignments_data = load_assignments_overview()
                
                return (
                    gr.update(value="✅ SPOC demoted to user successfully", visible=True),
                    gr.update(choices=all_user_choices),
                    gr.update(value=role_summary),
                    gr.update(choices=spoc_choices),
                    assignments_data
                )
            else:
                return (
                    gr.update(value="❌ Failed to demote SPOC to user", visible=True),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update()
                )
        
        def demote_spoc_to_user_handler(user_email):
            if not ui_service.is_admin() or not user_email:
                return gr.update(value="Please select a user", visible=True), gr.update(), gr.update(), gr.update(), gr.update()
            
            success = ui_service.demote_spoc_to_user(user_email)
            if success:
                # Refresh dropdowns
                users = ui_service.get_all_users_for_admin()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                spoc_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in spoc_users]
                
                # Update role summary
                role_summary = "**Current User Roles:**\n\n"
                role_summary += f"• Admins: {len([u for u in users if u['role'] == 'admin'])}\n"
                role_summary += f"• SPOCs: {len(spoc_users)}\n"
                role_summary += f"• Users: {len([u for u in users if u['role'] == 'user'])}\n\n"
                
                if spoc_users:
                    role_summary += "**SPOC Users:**\n"
                    for spoc in spoc_users:
                        role_summary += f"• {spoc['name']} ({spoc['email']})\n"
                
                # FIXED: Refresh assignments table
                assignments_data = load_assignments_overview()
                
                return (
                    gr.update(value="✅ User promoted to SPOC successfully", visible=True),
                    gr.update(choices=all_user_choices),
                    gr.update(value=role_summary),
                    gr.update(choices=spoc_choices),
                    assignments_data
                )
            else:
                return (
                    gr.update(value="❌ Failed to promote user to SPOC", visible=True),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update()
                )

        # Bind role management events with assignments table refresh
        promote_to_spoc_btn.click(
            fn=promote_user_to_spoc_handler,
            inputs=[role_management_dropdown],
            outputs=[assignment_status, role_management_dropdown, current_roles_display, spoc_email_dropdown, assignments_table]
        )
        
        demote_to_user_btn.click(
            fn=demote_spoc_to_user_handler,
            inputs=[role_management_dropdown],
            outputs=[assignment_status, role_management_dropdown, current_roles_display, spoc_email_dropdown, assignments_table]
        )
        
        # SPOC Management Functions
        def load_spoc_assignments_for_dropdown(spoc_email):
            if not ui_service.is_admin() or not spoc_email:
                return gr.update(choices=[], value=[])
            
            try:
                assigned_users = ui_service.get_spoc_assignments_for_spoc(spoc_email)
                
                # Get user details
                all_users = ui_service.get_all_users_for_admin()
                user_details = {user['email']: user['name'] for user in all_users}
                
                choices = [f"{user_details.get(email, email)} ({email})" for email in assigned_users]
                
                return gr.update(choices=choices, value=[])
            except Exception as e:
                return gr.update(choices=[], value=[])
        
        def add_spoc_assignment_handler(spoc_email, user_email):
            if not ui_service.is_admin() or not spoc_email or not user_email:
                return gr.update(value="Please select both SPOC and user", visible=True), gr.update(), gr.update()
            
            try:
                success = ui_service.add_spoc_assignment(spoc_email, user_email)
                if success:
                    # Refresh assignments list
                    assigned_users = ui_service.get_spoc_assignments_for_spoc(spoc_email)
                    all_users = ui_service.get_all_users_for_admin()
                    user_details = {user['email']: user['name'] for user in all_users}
                    choices = [f"{user_details.get(email, email)} ({email})" for email in assigned_users]
                    
                    # FIXED: Refresh overview table
                    overview_data = load_assignments_overview()
                    
                    return gr.update(value="✅ Assignment added successfully", visible=True), gr.update(choices=choices, value=[]), overview_data
                else:
                    return gr.update(value="❌ Failed to add assignment", visible=True), gr.update(), gr.update()
            except Exception as e:
                return gr.update(value=f"❌ Error: {str(e)}", visible=True), gr.update(), gr.update()
        
        def remove_spoc_assignments_handler(spoc_email, selected_assignments):
            if not ui_service.is_admin() or not spoc_email or not selected_assignments:
                return gr.update(value="Please select assignments to remove", visible=True), gr.update(), gr.update()
            
            try:
                removed_count = 0
                for assignment in selected_assignments:
                    # Extract email from "Name (email)" format
                    user_email = assignment.split("(")[-1].replace(")", "").strip()
                    if ui_service.remove_spoc_assignment(spoc_email, user_email):
                        removed_count += 1
                
                # Refresh assignments list
                assigned_users = ui_service.get_spoc_assignments_for_spoc(spoc_email)
                all_users = ui_service.get_all_users_for_admin()
                user_details = {user['email']: user['name'] for user in all_users}
                choices = [f"{user_details.get(email, email)} ({email})" for email in assigned_users]
                
                # FIXED: Refresh overview table
                overview_data = load_assignments_overview()
                
                return gr.update(value=f"✅ Removed {removed_count} assignments", visible=True), gr.update(choices=choices, value=[]), overview_data
            except Exception as e:
                return gr.update(value=f"❌ Error: {str(e)}", visible=True), gr.update(), gr.update()
        
        
        # FIXED: Manual refresh for assignments table
        def refresh_assignments_table():
            if ui_service.is_admin():
                assignments_data = load_assignments_overview()
                return assignments_data, gr.update(value="✅ Assignments table refreshed", visible=True)
            return gr.update(), gr.update(value="❌ Access denied", visible=True)
        
        # Bind SPOC management events with assignments table refresh
        current_spoc_dropdown.change(
            fn=load_spoc_assignments_for_dropdown,
            inputs=[current_spoc_dropdown],
            outputs=[assigned_users_list]
        )
        
        add_assignment_btn.click(
            fn=add_spoc_assignment_handler,
            inputs=[spoc_email_dropdown, user_email_dropdown],
            outputs=[assignment_status, assigned_users_list, assignments_table]
        )
        
        remove_assignment_btn.click(
            fn=remove_spoc_assignments_handler,
            inputs=[current_spoc_dropdown, assigned_users_list],
            outputs=[assignment_status, assigned_users_list, assignments_table]
        )
        
        # FIXED: Manual refresh button for assignments
        refresh_assignments_btn.click(
            fn=refresh_assignments_table,
            outputs=[assignments_table, assignment_status]
        )
        
        def refresh_users_handler():
            if ui_service.is_admin():
                users = ui_service.get_all_users_for_admin()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                regular_users = [user for user in users if user['role'] == 'user']
                all_user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                
                spoc_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in spoc_users]
                user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in regular_users]
                
                return (
                    gr.update(choices=all_user_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(choices=user_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(value="✅ Users refreshed", visible=True)
                )
            
            return (
                gr.update(choices=[]),
                gr.update(choices=[]),
                gr.update(choices=[]),
                gr.update(choices=[]),
                gr.update(value="❌ Access denied", visible=True)
            )
        
        refresh_users_btn.click(
            fn=refresh_users_handler,
            outputs=[role_management_dropdown, spoc_email_dropdown, user_email_dropdown, current_spoc_dropdown, assignment_status]
        )
        
        # Logout
        logout_btn.click(fn=lambda: None, js="() => { window.location.href = '/logout'; }")
    
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
        