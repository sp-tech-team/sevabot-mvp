from fastapi import Request, FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
import gradio as gr
from gradio.routes import mount_gradio_app

from auth import get_logged_in_user
from ui_service import ui_service
from user_management import user_management
from file_services import common_knowledge_service, user_file_service
from chat_service import chat_service

def create_landing_page_html() -> str:
    """Landing page HTML"""
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
            <div>🙏 Namaskaram, Welcome to</div>
            <h1 class="title">SEVABOT</h1>
            
            <div style="margin: 2rem 0;">
                <a href="/login" class="login-button">
                    <img src="https://developers.google.com/identity/images/btn_google_signin_dark_normal_web.png" 
                         alt="Sign in with Google" />
                </a>
            </div>
            
            <div class="domain-info">
                <strong>Access Restricted:</strong> Only whitelisted @sadhguru.org email addresses are permitted
            </div>
        </div>
    </body>
    </html>
    """

def create_gradio_interface():
    """Create main Gradio interface with all fixes"""
    
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
        
        # Main tabs
        with gr.Tabs():
            # Chat Tab
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
                            show_label=False
                        )
                    
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
                                    scale=3
                                )
                                refresh_chat_users_btn = gr.Button("🔄 Refresh Users", variant="secondary", scale=1)
                        
                        # Chat interface
                        chatbot = gr.Chatbot(
                            label="",
                            height="55vh",
                            show_copy_button=True,
                            show_share_button=False
                        )
                        
                        # Feedback row
                        with gr.Column(visible=False) as feedback_row:
                            gr.Markdown("**Rate how well the query is answered:**")
                            with gr.Row():
                                feedback_fully = gr.Button("✅ Fully", variant="secondary")
                                feedback_partially = gr.Button("⚠️ Partially", variant="secondary")
                                feedback_nopes = gr.Button("❌ Nopes", variant="secondary")
                            
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
                        
                        # Note and send button
                        with gr.Row():
                            gr.Markdown("*Press Shift+Enter to send message, Enter for new line*")
                            send_btn = gr.Button("Send", variant="primary", elem_classes="send-btn")
            
            # Files Tab (for regular users)
            with gr.TabItem("📄 Files", visible=False) as files_tab:
                gr.Markdown("## 📚 Knowledge Repository")
                gr.Markdown("*Browse the documents available in our knowledge repository*")
                
                with gr.Row():
                    user_file_search = gr.Textbox(
                        label="Search Files",
                        placeholder="Type to search files...",
                        interactive=True
                    )
                    refresh_user_files_btn = gr.Button("🔄 Refresh", variant="secondary")
                
                user_files_table = gr.Dataframe(
                    label="Available Documents",
                    headers=["Document Name", "Size", "Type", "Added Date"],
                    datatype=["str", "str", "str", "str"],
                    interactive=False,
                    wrap=True
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
                        user_vector_stats_btn = gr.Button("📊 Vector Stats", variant="secondary")
                    
                    # User Files Table
                    user_files_table = gr.Dataframe(
                        label="User Documents",
                        headers=["File Name", "Size", "Type", "Chunks", "Status", "Uploaded", "User"],
                        datatype=["str", "str", "str", "number", "str", "str", "str"],
                        interactive=False,
                        wrap=True
                    )
                    
                    # Status displays
                    user_upload_status = gr.Textbox(label="Upload Progress", visible=False, lines=6)
                    user_delete_status = gr.Textbox(label="Delete Progress", visible=False, lines=6)
                    user_vector_status = gr.Markdown(label="Vector Database Status", visible=False)
            
            # Users Tab
            with gr.TabItem("👥 Users", visible=False) as users_tab:
                with gr.Column(elem_classes="admin-section"):
                    gr.Markdown("## Admin User Management")
                    gr.Markdown("*Manage email whitelist and SPOC assignments*")
                    
                    # Email Whitelist Management
                    gr.Markdown("### 📧 Email Whitelist Management")
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### Add Email to Whitelist")
                            whitelist_email_input = gr.Textbox(
                                label="Email Address",
                                placeholder="user@sadhguru.org",
                                interactive=True
                            )
                            add_to_whitelist_btn = gr.Button("➕ Add to Whitelist", variant="primary")
                        
                        with gr.Column():
                            gr.Markdown("#### Current Whitelist")
                            whitelist_table = gr.Dataframe(
                                label="Whitelisted Emails",
                                headers=["Email", "Added By", "Date Added"],
                                datatype=["str", "str", "str"],
                                interactive=False,
                                wrap=True
                            )
                            
                            with gr.Row():
                                selected_whitelist_emails = gr.CheckboxGroup(
                                    label="Select emails to remove",
                                    choices=[],
                                    value=[]
                                )
                                remove_from_whitelist_btn = gr.Button("➖ Remove Selected", variant="secondary")
                    
                    # Role Management
                    gr.Markdown("### 🔧 Role Management")
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### View Users by Role")
                            
                            role_selection_dropdown = gr.Dropdown(
                                label="Select Role to View",
                                choices=[("Administrators", "admin"), ("SPOCs", "spoc"), ("Users", "user")],
                                value="admin",
                                interactive=True
                            )
                            
                            role_users_table = gr.Dataframe(
                                label="Users by Role",
                                headers=["Name", "Email", "Last Login", "Date Added"],
                                datatype=["str", "str", "str", "str"],
                                interactive=False,
                                wrap=True
                            )
                        
                        with gr.Column():
                            gr.Markdown("#### Role Actions")
                            
                            role_management_dropdown = gr.Dropdown(
                                label="Select User for Role Change",
                                choices=[],
                                value=None,
                                interactive=True,
                                filterable=True
                            )
                            
                            with gr.Row():
                                promote_to_spoc_btn = gr.Button("⬆️ Promote to SPOC", variant="primary")
                                demote_to_user_btn = gr.Button("⬇️ Demote to User", variant="secondary")
                    
                    # SPOC Assignments Section
                    gr.Markdown("### 📋 SPOC Assignments Management")
                    
                    # Assignments Overview
                    with gr.Row():
                        gr.Markdown("#### All SPOC Assignments Overview")
                        refresh_assignments_btn = gr.Button("🔄 Refresh Assignments", variant="secondary")
                    
                    assignments_table = gr.Dataframe(
                        label="",
                        headers=["SPOC Email", "SPOC Name", "Assigned User", "User Name", "Assignment Date"],
                        datatype=["str", "str", "str", "str", "str"],
                        interactive=False,
                        wrap=True
                    )
                    
                    with gr.Row():
                        # SPOC Assignment Section
                        with gr.Column():
                            gr.Markdown("#### Add SPOC Assignment")
                            
                            spoc_email_dropdown = gr.Dropdown(
                                label="Select SPOC",
                                choices=[],
                                value=None,
                                interactive=True,
                                filterable=True
                            )
                            
                            user_email_dropdown = gr.Dropdown(
                                label="Select User to Assign (from whitelist)",
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
                            gr.Markdown("#### Current SPOC Assignments")
                            
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
        
        # Copyright footer
        gr.HTML("""
        <div style="text-align: center; color: #9ca3af; font-size: 0.875rem; margin-top: 20px; padding: 15px;">
            <p>© Sadhguru, 2025 | This AI chat may make mistakes. Please use with discretion.</p>
        </div>
        """)
        
        # Hidden components for notifications
        file_notification = gr.HTML("", visible=False)
        action_status = gr.Textbox(visible=False)
        
        # ========== EVENT BINDINGS ==========
        
        # Load initial data
        demo.load(
            fn=ui_service.get_initial_visibility, 
            outputs=[
                namaskaram_user, sessions_radio, files_tab, file_manager_common_tab,
                file_manager_users_tab, users_tab, admin_chat_user_section,
                admin_upload_section, reindex_btn, cleanup_btn,
                file_manager_title, file_manager_guidelines, file_manager_container,
                chat_users_dropdown
            ]
        )
        
        # Load user files for regular users
        def load_user_files():
            if ui_service.get_user_role() == "user":
                files = common_knowledge_service.get_file_list_for_users()
                return gr.update(value=files)
            return gr.update(value=[])
        
        demo.load(fn=load_user_files, outputs=[user_files_table])
        
        # Load admin data
        def load_admin_data():
            if ui_service.is_admin():
                # Common knowledge files
                files = common_knowledge_service.get_file_list()
                choices = [row[0] for row in files] if files else []
                
                # Users data
                users = user_management.get_all_users()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_users_for_chat = [user for user in users if user['role'] in ['user', 'spoc', 'admin']]
                
                # Assignable users (from whitelist)
                assignable_users = user_management.get_assignable_users_for_spoc()
                
                all_user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                spoc_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in spoc_users]
                assignable_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in assignable_users]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in all_users_for_chat]
                
                user_file_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in users]
                admin_users_table = user_management.get_users_by_role("admin")
                
                # Whitelist data
                whitelist_data = user_management.get_whitelisted_emails()
                whitelist_table_data = [[item["email"], item["added_by"], item["added_at"][:10]] for item in whitelist_data]
                whitelist_choices = [item["email"] for item in whitelist_data]
                
                return (
                    gr.update(value=files), gr.update(choices=choices, value=[]),
                    gr.update(choices=all_user_choices), gr.update(choices=spoc_choices),
                    gr.update(choices=assignable_choices), gr.update(choices=spoc_choices),
                    gr.update(choices=chat_user_choices), gr.update(choices=user_file_choices),
                    gr.update(value=admin_users_table), gr.update(value=whitelist_table_data),
                    gr.update(choices=whitelist_choices)
                )
            elif ui_service.is_spoc():
                files = common_knowledge_service.get_file_list()
                assigned_users = user_management.get_spoc_assignments(ui_service.current_user["email"])
                users = user_management.get_all_users()
                assigned_user_details = [user for user in users if user['email'] in assigned_users]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in assigned_user_details]
                
                return tuple([gr.update(value=files)] + [gr.update()] * 6 + [gr.update(choices=chat_user_choices)] + [gr.update()] * 3)
            
            return tuple([gr.update()] * 11)
        
        demo.load(
            fn=load_admin_data,
            outputs=[
                files_table, selected_files, role_management_dropdown,
                spoc_email_dropdown, user_email_dropdown, current_spoc_dropdown,
                chat_users_dropdown, user_file_users_dropdown, role_users_table,
                whitelist_table, selected_whitelist_emails
            ]
        )
        
        # Load assignments overview
        def load_assignments_overview():
            if ui_service.is_admin():
                return gr.update(value=user_management.get_assignments_overview_table())
            return gr.update(value=[])
        
        demo.load(fn=load_assignments_overview, outputs=[assignments_table])
        
        # ========== CHAT HANDLERS ==========
        
        # FIXED: Chat user selection with proper conversation loading
        def select_user_for_chat(selected_user_email):
            if not ui_service.is_admin_or_spoc() or not selected_user_email:
                return gr.update()
            
            conversations = chat_service.get_user_conversations(selected_user_email)
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            
            return gr.update(choices=session_choices, value=None)
        
        def refresh_chat_users():
            if ui_service.is_admin():
                users = user_management.get_all_users()
                all_users_for_chat = [user for user in users if user['role'] in ['user', 'spoc', 'admin']]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in all_users_for_chat]
                return gr.update(choices=chat_user_choices)
            elif ui_service.is_spoc():
                assigned_users = user_management.get_spoc_assignments(ui_service.current_user["email"])
                users = user_management.get_all_users()
                assigned_user_details = [user for user in users if user['email'] in assigned_users]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in assigned_user_details]
                return gr.update(choices=chat_user_choices)
            
            return gr.update(choices=[])
        
        # FIXED: Refresh button working properly
        def refresh_current_user_chats():
            conversations = chat_service.get_user_conversations(ui_service.current_user["email"])
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            return gr.update(choices=session_choices, value=None)
        
        chat_users_dropdown.change(fn=select_user_for_chat, inputs=[chat_users_dropdown], outputs=[sessions_radio])
        refresh_chat_users_btn.click(fn=refresh_chat_users, outputs=[chat_users_dropdown])
        refresh_chat_btn.click(fn=refresh_current_user_chats, outputs=[sessions_radio])
        
        # Chat message handling
        def handle_send_message(message, history, conv_id):
            if not message.strip():
                return history, "", conv_id, gr.update(), "", gr.update(interactive=True), gr.update(visible=False), None
            
            new_history, empty_msg, new_conv_id, sessions_update, status = ui_service.send_message(message, history, conv_id)
            assistant_msg_id = ui_service.get_last_assistant_message_id()
            
            return new_history, empty_msg, new_conv_id, sessions_update, status, gr.update(interactive=False), gr.update(visible=True), assistant_msg_id
        
        message_input.submit(fn=handle_send_message, inputs=[message_input, chatbot, current_conversation_id], outputs=[chatbot, message_input, current_conversation_id, sessions_radio, action_status, message_input, feedback_row, last_assistant_message_id])
        send_btn.click(fn=handle_send_message, inputs=[message_input, chatbot, current_conversation_id], outputs=[chatbot, message_input, current_conversation_id, sessions_radio, action_status, message_input, feedback_row, last_assistant_message_id])
        
        # Session management
        new_chat_btn.click(fn=ui_service.create_new_chat, outputs=[chatbot, current_conversation_id, sessions_radio, action_status])
        sessions_radio.change(fn=ui_service.load_conversation, inputs=[sessions_radio], outputs=[chatbot, current_conversation_id, action_status])
        delete_chat_btn.click(fn=ui_service.delete_conversation, inputs=[sessions_radio], outputs=[chatbot, current_conversation_id, sessions_radio, action_status])
        
        # ========== FILE MANAGEMENT HANDLERS ==========
        
        # FIXED: File search functionality
        def handle_file_search(search_term):
            if ui_service.is_admin_or_spoc():
                files = common_knowledge_service.get_file_list(search_term)
                choices = [row[0] for row in files] if files else []
                return gr.update(value=files), gr.update(choices=choices, value=[])
            return gr.update(), gr.update()
        
        def handle_user_file_search(search_term):
            files = common_knowledge_service.get_file_list_for_users()
            if search_term:
                filtered_files = []
                search_lower = search_term.lower()
                for file_row in files:
                    if search_lower in " ".join(str(cell).lower() for cell in file_row):
                        filtered_files.append(file_row)
                files = filtered_files
            return gr.update(value=files)
        
        file_search_box.change(fn=handle_file_search, inputs=[file_search_box], outputs=[files_table, selected_files])
        user_file_search.change(fn=handle_user_file_search, inputs=[user_file_search], outputs=[user_files_table])
        
        # Common knowledge file operations
        def handle_ck_upload(files):
            if not ui_service.is_admin():
                notification = '<div class="notification">❌ Access denied - Admin only</div>'
                return gr.update(), gr.update(value="Access denied", visible=True), gr.update(), gr.update(value=notification, visible=True)
            
            files_list, status, choices = common_knowledge_service.upload_files(files, ui_service.current_user["email"])
            success_count = status.count("✅")
            notification = f'<div class="notification">📤 Upload Complete: {success_count} files processed</div>'
            return gr.update(value=files_list), gr.update(value=status, visible=True), gr.update(choices=choices, value=[]), gr.update(value=notification, visible=True)
        
        def handle_ck_delete(selected):
            if not ui_service.is_admin():
                notification = '<div class="notification">❌ Access denied - Admin only</div>'
                return gr.update(), gr.update(value="Access denied", visible=True), gr.update(), gr.update(value=notification, visible=True)
            
            files_list, status, choices = common_knowledge_service.delete_files(selected)
            success_count = status.count("✅")
            notification = f'<div class="notification">🗑️ Deletion Complete: {success_count} files removed</div>'
            return gr.update(value=files_list), gr.update(value=status, visible=True), gr.update(choices=choices, value=[]), gr.update(value=notification, visible=True)
        
        def handle_ck_refresh():
            if ui_service.is_admin_or_spoc():
                files = common_knowledge_service.get_file_list()
                choices = [row[0] for row in files] if files else []
                notification = '<div class="notification">🔄 Files refreshed</div>'
                return gr.update(value=files), gr.update(choices=choices, value=[]), gr.update(value=notification, visible=True)
            return gr.update(), gr.update(), gr.update(value='<div class="notification">❌ Access denied</div>', visible=True)
        
        def handle_ck_reindex():
            if ui_service.is_admin():
                result = common_knowledge_service.reindex_pending_files()
                files = common_knowledge_service.get_file_list()
                choices = [row[0] for row in files] if files else []
                notification = '<div class="notification">🔍 Re-indexing Complete</div>'
                return gr.update(value=files), gr.update(choices=choices), result, gr.update(value=notification, visible=True)
            return gr.update(), gr.update(), "Access denied", gr.update(value='<div class="notification">❌ Access denied</div>', visible=True)
        
        def select_all_files():
            if ui_service.is_admin_or_spoc():
                files = common_knowledge_service.get_file_list()
                all_files = [row[0] for row in files] if files else []
                return gr.update(value=all_files)
            return gr.update(value=[])
        
        # Bind common knowledge operations
        upload_btn.click(fn=handle_ck_upload, inputs=[file_upload], outputs=[files_table, upload_status, selected_files, file_notification])
        delete_btn.click(fn=handle_ck_delete, inputs=[selected_files], outputs=[files_table, delete_status, selected_files, file_notification])
        refresh_btn.click(fn=handle_ck_refresh, outputs=[files_table, selected_files, file_notification])
        reindex_btn.click(fn=handle_ck_reindex, outputs=[files_table, selected_files, action_status, file_notification])
        select_all_btn.click(fn=select_all_files, outputs=[selected_files])
        
        # FIXED: User file manager operations
        def select_user_for_file_manager(user_email):
            if ui_service.is_admin() and user_email:
                users = user_management.get_all_users()
                user_info = next((u for u in users if u['email'] == user_email), None)
                if user_info:
                    info_text = f"**Selected User:** {user_info['name']} ({user_info['email']})\n"
                    info_text += f"**Role:** {user_info['role'].upper()}\n"
                    info_text += f"**Last Login:** {user_info.get('last_login', 'Never')[:10] if user_info.get('last_login') else 'Never'}"
                    
                    # Load user files
                    user_files = user_file_service.get_user_file_list(user_email)
                    file_choices = [row[0] for row in user_files] if user_files else []
                    
                    return (
                        gr.update(value=info_text),
                        gr.update(value=user_files),
                        gr.update(choices=file_choices, value=[])
                    )
            return (
                gr.update(value="*No user selected*"),
                gr.update(value=[]),
                gr.update(choices=[], value=[])
            )
        
        def handle_user_file_upload(user_email, files):
            if not ui_service.is_admin() or not user_email:
                notification = '<div class="notification">❌ Admin access required and user must be selected</div>'
                return gr.update(), gr.update(value="Access denied or no user selected", visible=True), gr.update(), gr.update(value=notification, visible=True)
            
            files_list, status, choices = user_file_service.upload_files_for_user(user_email, files)
            success_count = status.count("✅")
            notification = f'<div class="notification">📤 Upload Complete: {success_count} files for user</div>'
            return gr.update(value=files_list), gr.update(value=status, visible=True), gr.update(choices=choices), gr.update(value=notification, visible=True)
        
        def handle_user_file_delete(user_email, selected_files):
            if not ui_service.is_admin() or not user_email:
                notification = '<div class="notification">❌ Admin access required and user must be selected</div>'
                return gr.update(), gr.update(value="Access denied or no user selected", visible=True), gr.update(), gr.update(value=notification, visible=True)
            
            files_list, status, choices = user_file_service.delete_user_files(user_email, selected_files)
            success_count = status.count("✅")
            notification = f'<div class="notification">🗑️ Deletion Complete: {success_count} files removed</div>'
            return gr.update(value=files_list), gr.update(value=status, visible=True), gr.update(choices=choices), gr.update(value=notification, visible=True)
        
        def refresh_user_file_users():
            if ui_service.is_admin():
                users = user_management.get_all_users()
                user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in users]
                notification = '<div class="notification">🔄 Users refreshed</div>'
                return gr.update(choices=user_choices), gr.update(value=notification, visible=True)
            return gr.update(choices=[]), gr.update(value="Access denied", visible=True)
        
        def handle_user_file_refresh(user_email):
            if ui_service.is_admin() and user_email:
                user_files = user_file_service.get_user_file_list(user_email)
                file_choices = [row[0] for row in user_files] if user_files else []
                notification = '<div class="notification">🔄 User files refreshed</div>'
                return gr.update(value=user_files), gr.update(choices=file_choices, value=[]), gr.update(value=notification, visible=True)
            return gr.update(), gr.update(), gr.update(value="No user selected", visible=True)
        
        def select_all_user_files(user_email):
            if ui_service.is_admin() and user_email:
                user_files = user_file_service.get_user_file_list(user_email)
                all_files = [row[0] for row in user_files] if user_files else []
                return gr.update(value=all_files)
            return gr.update(value=[])
        
        # Bind user file manager operations
        refresh_user_file_users_btn.click(fn=refresh_user_file_users, outputs=[user_file_users_dropdown, file_notification])
        user_file_users_dropdown.change(fn=select_user_for_file_manager, inputs=[user_file_users_dropdown], outputs=[user_file_selected_user_info, user_files_table, user_selected_files]).then(fn=lambda email: email, inputs=[user_file_users_dropdown], outputs=[selected_user_for_file_manager])
        user_upload_btn.click(fn=handle_user_file_upload, inputs=[selected_user_for_file_manager, user_file_upload], outputs=[user_files_table, user_upload_status, user_selected_files, file_notification])
        user_delete_btn.click(fn=handle_user_file_delete, inputs=[selected_user_for_file_manager, user_selected_files], outputs=[user_files_table, user_delete_status, user_selected_files, file_notification])
        user_refresh_btn.click(fn=handle_user_file_refresh, inputs=[selected_user_for_file_manager], outputs=[user_files_table, user_selected_files, file_notification])
        user_select_all_btn.click(fn=select_all_user_files, inputs=[selected_user_for_file_manager], outputs=[user_selected_files])
        
        # ========== USER MANAGEMENT HANDLERS ==========
        
        # Role management
        def promote_user_to_spoc(user_email):
            if not ui_service.is_admin() or not user_email:
                notification = '<div class="notification">❌ Please select a user</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)
            
            success = user_management.promote_user_to_spoc(user_email)
            if success:
                users = user_management.get_all_users()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                spoc_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in spoc_users]
                
                role_data = user_management.get_users_by_role("admin")
                assignments_data = user_management.get_assignments_overview_table()
                
                notification = '<div class="notification">✅ User promoted to SPOC successfully</div>'
                return (
                    gr.update(choices=all_user_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(value=role_data),
                    gr.update(value=assignments_data),
                    gr.update(value=notification, visible=True)
                )
            else:
                notification = '<div class="notification">❌ Failed to promote user to SPOC</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)
        
        def demote_spoc_to_user(user_email):
            if not ui_service.is_admin() or not user_email:
                notification = '<div class="notification">❌ Please select a user</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)
            
            success = user_management.demote_spoc_to_user(user_email)
            if success:
                users = user_management.get_all_users()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                spoc_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in spoc_users]
                
                role_data = user_management.get_users_by_role("admin")
                assignments_data = user_management.get_assignments_overview_table()
                
                notification = '<div class="notification">✅ SPOC demoted to user successfully</div>'
                return (
                    gr.update(choices=all_user_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(value=role_data),
                    gr.update(value=assignments_data),
                    gr.update(value=notification, visible=True)
                )
            else:
                notification = '<div class="notification">❌ Failed to demote SPOC to user</div>'
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)
        
        promote_to_spoc_btn.click(fn=promote_user_to_spoc, inputs=[role_management_dropdown], outputs=[role_management_dropdown, spoc_email_dropdown, current_spoc_dropdown, role_users_table, assignments_table, file_notification])
        demote_to_user_btn.click(fn=demote_spoc_to_user, inputs=[role_management_dropdown], outputs=[role_management_dropdown, spoc_email_dropdown, current_spoc_dropdown, role_users_table, assignments_table, file_notification])
        
        # Role selection for tabular view
        role_selection_dropdown.change(fn=lambda role: user_management.get_users_by_role(role) if ui_service.is_admin() and role else [], inputs=[role_selection_dropdown], outputs=[role_users_table])
        
        # Email whitelist management
        def add_email_to_whitelist(email):
            if ui_service.is_admin_or_spoc() and email:
                success = user_management.add_email_to_whitelist(email, ui_service.current_user["email"])
                if success:
                    whitelist_data = user_management.get_whitelisted_emails()
                    table_data = [[item["email"], item["added_by"], item["added_at"][:10]] for item in whitelist_data]
                    choices = [item["email"] for item in whitelist_data]
                    notification = '<div class="notification">✅ Email added to whitelist</div>'
                    return gr.update(value=table_data), gr.update(choices=choices, value=[]), gr.update(value=""), gr.update(value=notification, visible=True)
                else:
                    notification = '<div class="notification">❌ Email already exists or error occurred</div>'
                    return gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)
            
            notification = '<div class="notification">❌ Access denied or invalid email</div>'
            return gr.update(), gr.update(), gr.update(), gr.update(value=notification, visible=True)
        
        def remove_from_whitelist(selected_emails):
            if ui_service.is_admin_or_spoc() and selected_emails:
                removed_count = 0
                for email in selected_emails:
                    if user_management.remove_email_from_whitelist(email):
                        removed_count += 1
                
                whitelist_data = user_management.get_whitelisted_emails()
                table_data = [[item["email"], item["added_by"], item["added_at"][:10]] for item in whitelist_data]
                choices = [item["email"] for item in whitelist_data]
                notification = f'<div class="notification">✅ Removed {removed_count} emails from whitelist</div>'
                return gr.update(value=table_data), gr.update(choices=choices, value=[]), gr.update(value=notification, visible=True)
            
            notification = '<div class="notification">❌ No emails selected or access denied</div>'
            return gr.update(), gr.update(), gr.update(value=notification, visible=True)
        
        add_to_whitelist_btn.click(fn=add_email_to_whitelist, inputs=[whitelist_email_input], outputs=[whitelist_table, selected_whitelist_emails, whitelist_email_input, file_notification])
        remove_from_whitelist_btn.click(fn=remove_from_whitelist, inputs=[selected_whitelist_emails], outputs=[whitelist_table, selected_whitelist_emails, file_notification])
        
        # SPOC assignments - FIXED duplicate key handling
        def load_spoc_assignments_for_dropdown(spoc_email):
            if not ui_service.is_admin() or not spoc_email:
                return gr.update(choices=[], value=[])
            
            try:
                assigned_users = user_management.get_spoc_assignments(spoc_email)
                all_users = user_management.get_all_users()
                user_details = {user['email']: user['name'] for user in all_users}
                choices = [f"{user_details.get(email, email)} ({email})" for email in assigned_users]
                
                return gr.update(choices=choices, value=[])
            except Exception as e:
                return gr.update(choices=[], value=[])
        
        def add_spoc_assignment(spoc_email, user_email):
            if not ui_service.is_admin() or not spoc_email or not user_email:
                notification = '<div class="notification">❌ Please select both SPOC and user</div>'
                return gr.update(), gr.update(), gr.update(value=notification, visible=True)
            
            success = user_management.add_spoc_assignment(spoc_email, user_email)
            if success:
                assigned_users = user_management.get_spoc_assignments(spoc_email)
                all_users = user_management.get_all_users()
                user_details = {user['email']: user['name'] for user in all_users}
                choices = [f"{user_details.get(email, email)} ({email})" for email in assigned_users]
                
                overview_data = user_management.get_assignments_overview_table()
                notification = '<div class="notification">✅ Assignment added successfully</div>'
                return gr.update(choices=choices, value=[]), gr.update(value=overview_data), gr.update(value=notification, visible=True)
            else:
                notification = '<div class="notification">❌ Assignment already exists or failed to add</div>'
                return gr.update(), gr.update(), gr.update(value=notification, visible=True)
        
        def remove_spoc_assignments(spoc_email, selected_assignments):
            if not ui_service.is_admin() or not spoc_email or not selected_assignments:
                notification = '<div class="notification">❌ Please select assignments to remove</div>'
                return gr.update(), gr.update(), gr.update(value=notification, visible=True)
            
            try:
                removed_count = 0
                for assignment in selected_assignments:
                    user_email = assignment.split("(")[-1].replace(")", "").strip()
                    if user_management.remove_spoc_assignment(spoc_email, user_email):
                        removed_count += 1
                
                assigned_users = user_management.get_spoc_assignments(spoc_email)
                all_users = user_management.get_all_users()
                user_details = {user['email']: user['name'] for user in all_users}
                choices = [f"{user_details.get(email, email)} ({email})" for email in assigned_users]
                
                overview_data = user_management.get_assignments_overview_table()
                notification = f'<div class="notification">✅ Removed {removed_count} assignments</div>'
                return gr.update(choices=choices, value=[]), gr.update(value=overview_data), gr.update(value=notification, visible=True)
            except Exception as e:
                notification = f'<div class="notification">❌ Error: {str(e)}</div>'
                return gr.update(), gr.update(), gr.update(value=notification, visible=True)
        
        def refresh_users_handler():
            if ui_service.is_admin():
                users = user_management.get_all_users()
                assignable_users = user_management.get_assignable_users_for_spoc()
                spoc_users = [user for user in users if user['role'] == 'spoc']
                all_user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                
                spoc_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in spoc_users]
                assignable_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in assignable_users]
                
                notification = '<div class="notification">✅ Users refreshed</div>'
                return (
                    gr.update(choices=all_user_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(choices=assignable_choices),
                    gr.update(choices=spoc_choices),
                    gr.update(value=notification, visible=True)
                )
            
            notification = '<div class="notification">❌ Access denied</div>'
            return tuple([gr.update(choices=[])] * 4 + [gr.update(value=notification, visible=True)])
        
        # Bind SPOC assignment operations
        current_spoc_dropdown.change(fn=load_spoc_assignments_for_dropdown, inputs=[current_spoc_dropdown], outputs=[assigned_users_list])
        add_assignment_btn.click(fn=add_spoc_assignment, inputs=[spoc_email_dropdown, user_email_dropdown], outputs=[assigned_users_list, assignments_table, file_notification])
        remove_assignment_btn.click(fn=remove_spoc_assignments, inputs=[current_spoc_dropdown, assigned_users_list], outputs=[assigned_users_list, assignments_table, file_notification])
        refresh_assignments_btn.click(fn=lambda: gr.update(value=user_management.get_assignments_overview_table()) if ui_service.is_admin() else gr.update(), outputs=[assignments_table])
        refresh_users_btn.click(fn=refresh_users_handler, outputs=[role_management_dropdown, spoc_email_dropdown, user_email_dropdown, current_spoc_dropdown, file_notification])
        
        # Feedback handlers
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

        for feedback_btn, feedback_type in [(feedback_fully, "fully"), (feedback_partially, "partially"), (feedback_nopes, "nopes")]:
            feedback_btn.click(
                fn=lambda msg_id, remarks, hist, ftype=feedback_type: handle_feedback(ftype, msg_id, remarks, hist),
                inputs=[last_assistant_message_id, feedback_remarks, chatbot],
                outputs=[message_input, feedback_row, chatbot, feedback_remarks, feedback_warning]
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
    mount_gradio_app(app, demo, path="/gradio")# ui.py - Main UI file with all fixes