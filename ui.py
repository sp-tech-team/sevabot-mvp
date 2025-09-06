# ui.py - Complete version with all requested improvements
from fastapi import Request, FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
import gradio as gr
from gradio.routes import mount_gradio_app

from auth import get_logged_in_user
from ui_service import ui_service
from config import IS_PRODUCTION

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
            
            .guidelines {
                margin-top: 1rem;
                padding: 1rem;
                background: #f0f9ff;
                border-radius: 8px;
                font-size: 0.85rem;
                color: #0369a1;
                border-left: 3px solid #0ea5e9;
                text-align: left;
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
    """Create Gradio interface with tabs and improved layout"""
    
    with gr.Blocks(
        theme=gr.themes.Soft(), 
        title="SEVABOT",
        head="""
        <style>
        /* Hide Gradio footer */
        .gradio-container .footer {
            display: none !important;
        }
        .gradio-container footer {
            display: none !important;
        }
        footer[data-testid="footer"] {
            display: none !important;
        }
        .gradio-container > div:last-child {
            display: none !important;
        }
        </style>
        """,
        css="""
        /* Use modern font stack */
        .gradio-container, .main, *, html, body, div, span, h1, h2, h3, h4, h5, h6, p, a, button, input, textarea, select, label {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif !important;
        }
        
        /* Logo styling */
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
        
        /* Logout button styling */
        .logout-btn { 
            background-color: #dc2626 !important; 
            color: white !important;
            width: auto !important;
            min-width: 85px !important;
            padding: 8px 16px !important;
            font-size: 14px !important;
        }
        
        /* Send button styling - normal font size */
        .send-btn {
            background-color: #667eea !important;
            color: white !important;
            font-weight: 600 !important;
            min-width: 60px !important;
            max-width: 80px !important;
            padding: 8px 16px !important;
            font-size: 14px !important;
        }
        
        /* Notification with auto-fade */
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
        
        /* Feedback buttons */
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
        
        /* Admin section styling */
        .admin-section {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%) !important;
            border: 1px solid rgba(102, 126, 234, 0.2) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            margin-bottom: 20px !important;
        }
        
        /* Copyright footer - greyish */
        .copyright-footer {
            text-align: center !important;
            color: #9ca3af !important;
            font-size: 0.875rem !important;
            margin-top: 20px !important;
            padding: 15px !important;
        }
        
        /* Other UI elements */
        .sessions-list, .chat-interface { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif !important; }
        .tab-nav button { font-size: 1.1em !important; font-weight: 600 !important; padding: 0.6em 1.2em !important; }
        .gradio-container { height: 100vh !important; }
        .main { height: calc(100vh - 80px) !important; overflow-y: auto !important; }
        
        /* Button normal sizes */
        .btn, .btn-primary, .btn-secondary { 
            font-size: 14px !important;
            padding: 8px 16px !important;
            min-height: auto !important;
            width: auto !important;
        }
        
        /* Scrolling fixes */
        .block { overflow: visible !important; }
        .panel-wrap { overflow: visible !important; }
        .app { overflow-y: auto !important; height: 100vh !important; }
        """) as demo:
        
        # State variables
        current_conversation_id = gr.State(None)
        last_assistant_message_id = gr.State(None)
        selected_user_for_admin = gr.State(None)
        selected_chat_user = gr.State(None)
        
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
                    # User greeting using gradio Button for light background
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
                            refresh_chat_btn = gr.Button("🔄 Refresh Chat", variant="secondary")
                        
                        sessions_radio = gr.Radio(
                            label="Conversations",
                            choices=[],
                            value=None,
                            interactive=True,
                            show_label=False,
                            elem_classes="sessions-list"
                        )
                        
                        # User file list (visible to regular users)
                        with gr.Column(visible=False) as user_files_section:
                            gr.Markdown("### 📋 Your Documents")
                            gr.Markdown("*Files uploaded by administrators*")
                            
                            user_files_table = gr.Dataframe(
                                label="",
                                headers=["File Name", "Size", "Status"],
                                datatype=["str", "str", "str"],
                                interactive=False,
                                wrap=True
                            )
                            
                            refresh_user_files_btn = gr.Button("🔄 Refresh Files", variant="secondary", size="sm")
                    
                    # Main content area
                    with gr.Column(scale=4):
                        # Admin user selection for chat viewing
                        with gr.Column(visible=False) as admin_chat_user_section:
                            gr.Markdown("#### 👑 Admin: View User Chats")
                            
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
                            placeholder="Ask me anything about your documents...",
                            lines=3,
                            max_lines=6,
                            show_label=False,
                            interactive=True
                        )
                        
                        # Note and send button in same line
                        with gr.Row():
                            gr.Markdown("*Press Shift+Enter to send message, Enter for new line*")
                            send_btn = gr.Button("📤 Send", variant="primary", elem_classes="send-btn")
            
            # File Manager Tab (for admins only)
            with gr.TabItem("📁 File Manager", visible=False) as file_manager_tab:
                with gr.Column(elem_classes="admin-section"):
                    gr.Markdown("## 👑 Admin File Management")
                    
                    # Document Guidelines
                    gr.Markdown("""
                    **📋 Document Guidelines:**
                    • Max file size: 10MB | Supported formats: .txt, .md, .pdf, .docx | PDFs must be text-extractable (OCR not supported)
                    """)
                    
                    with gr.Row():
                        users_dropdown = gr.Dropdown(
                            label="Search & Select User",
                            choices=[],
                            value=None,
                            interactive=True,
                            allow_custom_value=False,
                            filterable=True,
                            scale=3
                        )
                        refresh_users_btn = gr.Button("🔄 Refresh Users", variant="secondary", scale=1)
                    
                    selected_user_info = gr.Markdown("*No user selected*")
                    
                    # Admin file management
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
                    
                    # Admin file list
                    gr.Markdown("### 📋 Documents")
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 Refresh")
                        reindex_btn = gr.Button("🔍 Re-index")
                        cleanup_btn = gr.Button("🧹 Cleanup", variant="secondary")
                        vector_stats_btn = gr.Button("📊 Vector Stats", variant="secondary")
                    
                    files_table = gr.Dataframe(
                        label="",
                        headers=["File Name", "Size", "Chunks", "Status", "Source", "Vector Status", "Uploaded", "User"],
                        datatype=["str", "str", "number", "str", "str", "str", "str", "str"],
                        interactive=False,
                        wrap=True
                    )
                    
                    # Status displays for admin
                    upload_status = gr.Textbox(label="Upload Progress", visible=False, lines=6)
                    delete_status = gr.Textbox(label="Delete Progress", visible=False, lines=6)
                    vector_status = gr.Textbox(label="Vector Database Status", visible=False, lines=6)
        
        # Copyright footer - greyish
        gr.HTML("""
        <div class="copyright-footer">
            <p>© Sadhguru, 2025 | This AI chat may make mistakes. Please use with discretion.</p>
        </div>
        """)
        
        # Hidden components
        action_status = gr.Textbox(visible=False)
        file_notification = gr.HTML("", visible=False)
        
        # Load initial data and auto-load users for admins
        def load_initial_data():
            user_name = ui_service.get_display_name()
            is_admin = ui_service.is_admin()
            
            # User greeting in one line using Button for light background
            if is_admin:
                greeting = f"Namaskaram {user_name}! [ADMIN]"
            else:
                greeting = f"Namaskaram {user_name}!"
            
            sessions_update = ui_service.load_initial_data()[1]
            
            # Visibility based on role
            file_manager_visible = is_admin
            admin_chat_section_visible = is_admin
            user_files_visible = not is_admin
            
            # Auto-load users for admin on startup
            if is_admin:
                users = ui_service.get_all_users_for_admin()
                user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
                chat_user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in users]
                users_info = f"*Found {len(users)} users*"
            else:
                user_choices = []
                chat_user_choices = []
                users_info = "*No user selected*"
            
            return (
                greeting,
                sessions_update,
                gr.update(visible=file_manager_visible),
                gr.update(visible=admin_chat_section_visible),
                gr.update(visible=user_files_visible),
                gr.update(choices=user_choices),
                gr.update(choices=chat_user_choices),
                users_info
            )
        
        demo.load(
            fn=load_initial_data, 
            outputs=[
                namaskaram_user, 
                sessions_radio, 
                file_manager_tab,
                admin_chat_user_section,
                user_files_section,
                users_dropdown,
                chat_users_dropdown,
                selected_user_info
            ]
        )
        
        # Load user's own files for regular users
        def load_user_files():
            if ui_service.is_admin():
                return gr.update(value=[])
            
            files = ui_service.get_file_list()
            user_files = [[f[0], f[1], f[3]] for f in files] if files else []
            return gr.update(value=user_files)
        
        demo.load(fn=load_user_files, outputs=[user_files_table])
        
        # Admin user management functions
        def load_users_for_admin():
            if not ui_service.is_admin():
                return gr.update(choices=[]), "*Access denied*"
            
            users = ui_service.get_all_users_for_admin()
            user_choices = [(f"{user['name']} ({user['email']}) - {user['role'].upper()}", user['email']) for user in users]
            
            return gr.update(choices=user_choices), f"*Found {len(users)} users*"
        
        def load_users_for_chat():
            if not ui_service.is_admin():
                return gr.update(choices=[]), "*Access denied*"
            
            users = ui_service.get_all_users_for_admin()
            user_choices = [(f"{user['name']} ({user['email']})", user['email']) for user in users]
            
            return gr.update(choices=user_choices), f"*Found {len(users)} users*"
        
        def select_user_for_admin(selected_user_email):
            if not ui_service.is_admin() or not selected_user_email:
                return "*No user selected*", gr.update(), gr.update()
            
            files = ui_service.get_enhanced_user_files_for_admin(selected_user_email)
            user_info = f"**📁 Managing files for:** `{selected_user_email}`"
            
            choices = [row[0] for row in files] if files else []
            
            return user_info, gr.update(value=files), gr.update(choices=choices, value=[])
        
        def select_user_for_chat(selected_user_email):
            if not ui_service.is_admin() or not selected_user_email:
                return gr.update(), selected_user_email
            
            conversations = ui_service.get_user_conversations_for_admin(selected_user_email)
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            
            return gr.update(choices=session_choices, value=None), selected_user_email
        
        def refresh_selected_user_chat(selected_user_email):
            if not ui_service.is_admin() or not selected_user_email:
                return gr.update()
            
            conversations = ui_service.get_user_conversations_for_admin(selected_user_email)
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            
            return gr.update(choices=session_choices, value=None)
        
        def get_vector_stats(selected_user_email):
            if not ui_service.is_admin() or not selected_user_email:
                return gr.update(value="Please select a user first", visible=True)
            
            stats = ui_service.get_vector_database_stats(selected_user_email)
            return gr.update(value=stats, visible=True)
        
        # Bind admin events
        refresh_users_btn.click(
            fn=load_users_for_admin,
            outputs=[users_dropdown, selected_user_info]
        )
        
        refresh_chat_users_btn.click(
            fn=load_users_for_chat,
            outputs=[chat_users_dropdown]
        )
        
        refresh_chat_btn.click(
            fn=refresh_selected_user_chat,
            inputs=[selected_chat_user],
            outputs=[sessions_radio]
        )
        
        users_dropdown.change(
            fn=select_user_for_admin,
            inputs=[users_dropdown],
            outputs=[selected_user_info, files_table, selected_files]
        ).then(
            fn=lambda email: email,
            inputs=[users_dropdown],
            outputs=[selected_user_for_admin]
        )
        
        chat_users_dropdown.change(
            fn=select_user_for_chat,
            inputs=[chat_users_dropdown],
            outputs=[sessions_radio, selected_chat_user]
        )
        
        vector_stats_btn.click(
            fn=get_vector_stats,
            inputs=[selected_user_for_admin],
            outputs=[vector_status]
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
                warning_msg = f"⚠️ **Warning:** Please provide feedback remarks for '{feedback_type.title()}' rating."
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
                error_msg = f"❌ **Error:** Failed to submit feedback: {str(e)}"
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
        
        # File operations for admins with auto-refresh after cleanup/delete
        def handle_upload_complete(files, selected_user_email):
            if ui_service.is_admin() and selected_user_email:
                files_update, status, choices_update = ui_service.upload_files_for_user(files, selected_user_email)
                success_count = status.count("✅")
                notification = f'<div class="notification">📤 Upload Complete: {success_count} files processed</div>'
                
                enhanced_files = ui_service.get_enhanced_user_files_for_admin(selected_user_email)
                admin_choices = [row[0] for row in enhanced_files] if enhanced_files else []
                
                return gr.update(value=enhanced_files), gr.update(value=status, visible=True), gr.update(choices=admin_choices, value=[]), gr.update(value=notification, visible=True)
            else:
                return gr.update(), gr.update(value="Please select a user first", visible=True), gr.update(), gr.update(value='<div class="notification">❌ Select a user first</div>', visible=True)

        upload_btn.click(
            fn=handle_upload_complete, 
            inputs=[file_upload, selected_user_for_admin], 
            outputs=[files_table, upload_status, selected_files, file_notification]
        )
        
        def handle_delete_complete(selected, selected_user_email):
            if ui_service.is_admin() and selected_user_email:
                files_update, status, choices_update = ui_service.delete_files_with_progress(selected, selected_user_email)
                success_count = status.count("✅")
                notification = f'<div class="notification">🗑️ Deletion Complete: {success_count} files removed</div>'
                
                # Auto-refresh file list after deletion
                enhanced_files = ui_service.get_enhanced_user_files_for_admin(selected_user_email)
                admin_choices = [row[0] for row in enhanced_files] if enhanced_files else []
                
                return gr.update(value=enhanced_files), gr.update(value=status, visible=True), gr.update(choices=admin_choices, value=[]), gr.update(value=notification, visible=True)
            else:
                return gr.update(), gr.update(value="Please select a user first", visible=True), gr.update(), gr.update(value='<div class="notification">❌ Select a user first</div>', visible=True)
        
        delete_btn.click(
            fn=handle_delete_complete, 
            inputs=[selected_files, selected_user_for_admin], 
            outputs=[files_table, delete_status, selected_files, file_notification]
        )
        
        def select_all_files(selected_user_email):
            if ui_service.is_admin() and selected_user_email:
                files = ui_service.get_enhanced_user_files_for_admin(selected_user_email)
                all_files = [row[0] for row in files] if files else []
                return gr.update(value=all_files)
            return gr.update(value=[])
        
        select_all_btn.click(
            fn=select_all_files,
            inputs=[selected_user_for_admin],
            outputs=[selected_files]
        )
        
        # Regular user file refresh
        def handle_refresh_user_files():
            files = ui_service.get_file_list()
            user_files = [[f[0], f[1], f[3]] for f in files] if files else []
            notification = '<div class="notification">🔄 Files refreshed</div>'
            return gr.update(value=user_files), gr.update(value=notification, visible=True)
        
        refresh_user_files_btn.click(
            fn=handle_refresh_user_files,
            outputs=[user_files_table, file_notification]
        )
        
        # Admin file management with auto-refresh
        def handle_refresh_with_notification(selected_user_email):
            if ui_service.is_admin() and selected_user_email:
                files = ui_service.get_enhanced_user_files_for_admin(selected_user_email)
                choices = [row[0] for row in files] if files else []
                notification = f'<div class="notification">🔄 Files refreshed</div>'
                return gr.update(value=files), gr.update(choices=choices, value=[]), gr.update(value=notification, visible=True)
            else:
                return gr.update(), gr.update(), gr.update(value='<div class="notification">❌ Select a user first</div>', visible=True)
        
        refresh_btn.click(
            fn=handle_refresh_with_notification,
            inputs=[selected_user_for_admin],
            outputs=[files_table, selected_files, file_notification]
        )
        
        def handle_reindex_with_notification(selected_user_email):
            if ui_service.is_admin() and selected_user_email:
                result = ui_service.reindex_pending_files(selected_user_email)
                # Auto-refresh after re-indexing
                files = ui_service.get_enhanced_user_files_for_admin(selected_user_email)
                choices = [row[0] for row in files] if files else []
                notification = f'<div class="notification">🔍 Re-indexing Complete</div>'
                return gr.update(value=files), gr.update(choices=choices), result, gr.update(value=notification, visible=True)
            else:
                return gr.update(), gr.update(), "Please select a user first", gr.update(value='<div class="notification">❌ Select a user first</div>', visible=True)
        
        reindex_btn.click(
            fn=handle_reindex_with_notification,
            inputs=[selected_user_for_admin],
            outputs=[files_table, selected_files, action_status, file_notification]
        )
        
        def handle_cleanup_with_notification(selected_user_email):
            if ui_service.is_admin() and selected_user_email:
                result = ui_service.cleanup_vector_database(selected_user_email)
                # Auto-refresh after cleanup
                files = ui_service.get_enhanced_user_files_for_admin(selected_user_email)
                choices = [row[0] for row in files] if files else []
                notification = f'<div class="notification">🧹 Cleanup Complete</div>'
                return result, gr.update(value=files), gr.update(choices=choices, value=[]), gr.update(value=notification, visible=True)
            else:
                return "Please select a user first", gr.update(), gr.update(), gr.update(value='<div class="notification">❌ Select a user first</div>', visible=True)
        
        cleanup_btn.click(
            fn=handle_cleanup_with_notification,
            inputs=[selected_user_for_admin],
            outputs=[action_status, files_table, selected_files, file_notification]
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