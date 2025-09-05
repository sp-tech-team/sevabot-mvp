# ui.py - Updated with minimal design and modern fonts
from fastapi import Request, FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
import gradio as gr
from gradio.routes import mount_gradio_app

from auth import get_logged_in_user
from ui_service import ui_service

def create_landing_page_html() -> str:
    """Minimal login page design with access restriction retained"""
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
    """Create Gradio interface with modern fonts and improved features"""
    
    with gr.Blocks(theme=gr.themes.Soft(), title="SEVABOT", css="""
        /* Use modern font stack similar to Claude/GPT */
        .gradio-container, .main, *, html, body, div, span, h1, h2, h3, h4, h5, h6, p, a, button, input, textarea, select, label {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif !important;
        }
        
        /* Logo styling - clean and minimal */
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
        
        /* User greeting */
        .user-greeting { 
            color: #555 !important;
            font-size: 0.95rem !important;
            margin: 0 !important;
            margin-right: 12px !important;
            font-weight: 500 !important;
            white-space: nowrap !important;
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
        
        /* Lighter feedback buttons for better emoji visibility */
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
        
        /* Notification popup styling */
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
        }
        
        /* Other UI elements */
        .sessions-list, .chat-interface { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif !important; }
        .tab-nav button { font-size: 1.1em !important; font-weight: 600 !important; padding: 0.6em 1.2em !important; }
        .gradio-container { height: 100vh !important; }
        .main { height: calc(100vh - 120px) !important; overflow-y: auto !important; }
        
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
        
        # Header with enhanced SEVABOT logo
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
                    namaskaram_user = gr.Markdown("(Namaskaram **User**!)", elem_classes="user-greeting")
                    logout_btn = gr.Button("Logout", variant="stop", elem_classes="logout-btn")
        
        # Main tabs
        with gr.Tabs():
            # Chat Tab
            with gr.TabItem("💬 Chat"):
                with gr.Row():
                    # Left sidebar - Sessions
                    with gr.Column(scale=1, min_width=250):
                        gr.Markdown("### Chat Sessions")
                        with gr.Row():
                            new_chat_btn = gr.Button("New", variant="primary")
                            delete_chat_btn = gr.Button("Delete", variant="secondary")
                        
                        sessions_radio = gr.Radio(
                            label="Conversations",
                            choices=[],
                            value=None,
                            interactive=True,
                            show_label=False,
                            elem_classes="sessions-list"
                        )
                    
                    # Main chat area
                    with gr.Column(scale=4):
                        chatbot = gr.Chatbot(
                            label="",
                            height="65vh",
                            show_copy_button=True,
                            show_share_button=False,
                            elem_classes="chat-interface"
                        )
                        
                        # Enhanced feedback row with lighter button colors
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
                        
                        message_input = gr.Textbox(
                            label="",
                            placeholder="Ask me anything about your documents...",
                            lines=3,
                            max_lines=6,
                            show_label=False,
                            interactive=True
                        )
                        gr.Markdown("*Press Shift+Enter to send message, Enter for new line*")
            
            # File Manager Tab
            with gr.TabItem("📁 File Manager"):
                gr.Markdown("## 📁 Document Management")
                
                # Shortened file upload guidelines
                gr.Markdown("""
                **📋 File Upload Guidelines:**
                - Supported formats: `.txt`, `.md`, `.pdf`, `.docx` (max 10MB)
                - Prefer uploading docs and txts over pdfs to save space and better readability
                """)
                
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
                        upload_btn = gr.Button("Upload Files", variant="primary")
                        upload_status = gr.Textbox(label="Upload Progress", interactive=False, lines=6, visible=False)
                    
                    # Delete section
                    with gr.Column():
                        gr.Markdown("### 🗑️ Delete Documents")
                        selected_files = gr.CheckboxGroup(
                            label="Select files (Ctrl+Shift for multiple)",
                            choices=[],
                            value=[]
                        )
                        with gr.Row():
                            delete_btn = gr.Button("Delete Selected", variant="secondary")
                            select_all_btn = gr.Button("Select All", variant="secondary")
                        delete_status = gr.Textbox(label="Delete Progress", interactive=False, lines=6, visible=False)
                
                gr.Markdown("### 📋 Your Documents")
                with gr.Row():
                    refresh_btn = gr.Button("Refresh List")
                    reindex_btn = gr.Button("Re-index Pending")
                    cleanup_btn = gr.Button("Refresh Knowledge Base", variant="secondary")
                
                files_table = gr.Dataframe(
                    label="",
                    headers=["File Name", "Size", "Chunks", "Status", "Uploaded"],
                    datatype=["str", "str", "number", "str", "str"],
                    interactive=False,
                    wrap=True
                )
                
                # File manager notification
                file_notification = gr.HTML("", visible=False)
        
        # Hidden components
        action_status = gr.Textbox(visible=False)
        
        # Event Handlers
        def load_initial_data():
            user_name = ui_service.get_display_name()
            namaskaram_msg = f"(Namaskaram **{user_name}**!)"
            sessions_update = ui_service.load_initial_data()[1]
            return namaskaram_msg, sessions_update
        
        demo.load(fn=load_initial_data, outputs=[namaskaram_user, sessions_radio])
        
        # Load file data
        def safe_load_file_data():
            try:
                files = ui_service.get_file_list()
                choices = [row[0] for row in files] if files and len(files) > 0 else []
                return gr.update(value=files), gr.update(choices=choices, value=[])
            except Exception as e:
                return gr.update(value=[]), gr.update(choices=[], value=[])

        demo.load(fn=safe_load_file_data, outputs=[files_table, selected_files])
        
        # Chat message handling
        def handle_send_message(message, history, conv_id):
            if not message.strip():
                return history, "", conv_id, gr.update(), "", gr.update(interactive=True), gr.update(visible=False), None
            
            new_history, empty_msg, new_conv_id, sessions_update, status = ui_service.send_message(message, history, conv_id)
            assistant_msg_id = ui_service.get_last_assistant_message_id()
            
            return new_history, empty_msg, new_conv_id, sessions_update, status, gr.update(interactive=False), gr.update(visible=True), assistant_msg_id
        
        message_input.submit(
            fn=handle_send_message,
            inputs=[message_input, chatbot, current_conversation_id],
            outputs=[chatbot, message_input, current_conversation_id, sessions_radio, action_status, message_input, feedback_row, last_assistant_message_id]
        )
        
        # Enhanced feedback handlers with mandatory remarks for Partially/Nopes
        def handle_feedback(feedback_type, message_id, remarks, history):
            if not message_id:
                return gr.update(interactive=True), gr.update(visible=False), history, "", gr.update(visible=False)
            
            # Check for mandatory remarks on Partially/Nopes
            if feedback_type in ["partially", "nopes"] and (not remarks or not remarks.strip()):
                warning_msg = f"⚠️ **Warning:** Please provide feedback remarks for '{feedback_type.title()}' rating to help improve responses."
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
        
        # File operations with notifications
        def handle_upload_start(files):
            if not files:
                return gr.update(visible=True, value="No files selected")
            return gr.update(visible=True, value="Starting upload...")

        def handle_upload_complete(files):
            files_update, status, choices_update = ui_service.upload_files_with_progress(files)
            success_count = status.count("✅")
            notification = f'<div class="notification">📤 Upload Complete: {success_count} files processed</div>'
            return files_update, gr.update(value=status), choices_update, gr.update(value=notification, visible=True)

        upload_btn.click(fn=handle_upload_start, inputs=[file_upload], outputs=[upload_status]).then(
            fn=handle_upload_complete, inputs=[file_upload], outputs=[files_table, upload_status, selected_files, file_notification]
        )
        
        def handle_delete_start(selected):
            if not selected:
                return gr.update(visible=True, value="No files selected")
            return gr.update(visible=True, value="Starting deletion...")

        def handle_delete_complete(selected):
            files_update, status, choices_update = ui_service.delete_files_with_progress(selected)
            success_count = status.count("✅")
            notification = f'<div class="notification">🗑️ Deletion Complete: {success_count} files removed</div>'
            return files_update, gr.update(value=status), choices_update, gr.update(value=notification, visible=True)
        
        delete_btn.click(fn=handle_delete_start, inputs=[selected_files], outputs=[delete_status]).then(
            fn=handle_delete_complete, inputs=[selected_files], outputs=[files_table, delete_status, selected_files, file_notification]
        )
        
        def select_all_files():
            files = ui_service.get_file_list()
            all_files = [row[0] for row in files] if files else []
            return gr.update(value=all_files)
        
        select_all_btn.click(fn=select_all_files, outputs=[selected_files])
        
        def handle_refresh_with_notification():
            files_update, choices_update = safe_load_file_data()
            notification = '<div class="notification">🔄 File list refreshed successfully</div>'
            return files_update, choices_update, gr.update(value=notification, visible=True)
        
        refresh_btn.click(fn=handle_refresh_with_notification, outputs=[files_table, selected_files, file_notification])
        
        def handle_reindex_with_notification():
            result = ui_service.reindex_pending_files()
            files = ui_service.get_file_list()
            choices = [row[0] for row in files] if files else []
            reindexed_count = result.count("Re-indexed")
            notification = f'<div class="notification">🔍 Re-indexing Complete: {reindexed_count} files processed</div>'
            return gr.update(value=files), gr.update(choices=choices), result, gr.update(value=notification, visible=True)
        
        reindex_btn.click(fn=handle_reindex_with_notification, outputs=[files_table, selected_files, action_status, file_notification])
        
        # Enhanced cleanup with notification
        def handle_cleanup_with_notification():
            result = ui_service.cleanup_vector_database()
            cleaned_count = 0
            if "Cleaned" in result:
                try:
                    import re
                    numbers = re.findall(r'\d+', result)
                    if numbers:
                        cleaned_count = sum(int(n) for n in numbers[:2])
                except:
                    pass
            
            if "clean" in result.lower() and cleaned_count == 0:
                notification = '<div class="notification">✅ Knowledge base is already clean</div>'
            else:
                notification = f'<div class="notification">🧹 Knowledge Base Refreshed: {cleaned_count} orphaned entries cleaned</div>'
            
            return result, gr.update(value=notification, visible=True)
        
        cleanup_btn.click(fn=handle_cleanup_with_notification, outputs=[action_status, file_notification])
        
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
        return RedirectResponse("/gradio/")  # Fixed: Add trailing slash

    @app.get("/chat")
    async def chat_redirect(request: Request):
        return RedirectResponse("/")
    
    # FIXED: Corrected middleware logic
    @app.middleware("http")
    async def auth_middleware(request, call_next):
        # Only apply auth check to gradio routes
        if request.url.path.startswith("/gradio"):
            user_data = get_logged_in_user(request)
            if not user_data:
                # Only redirect if user is NOT authenticated
                return RedirectResponse("/")
            # Set user data if authenticated
            ui_service.set_user(user_data)
        
        # IMPORTANT: Always call next for gradio routes when user IS authenticated
        response = await call_next(request)
        return response
    
    # Mount Gradio interface
    demo = create_gradio_interface()
    mount_gradio_app(app, demo, path="/gradio")