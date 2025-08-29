# ui.py - Clean UI with enhanced feedback handling
from fastapi import Request, FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
import gradio as gr
from gradio.routes import mount_gradio_app
from typing import List, Any

from auth import get_logged_in_user
from ui_service import ui_service

def create_landing_page_html() -> str:
    """Simple login page as requested"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to Sevabot</title>
    </head>
    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f8f9fa;">
        <h1>🙏 Namaskaram! 🙏</h1>
        <p>Welcome to Sevabot</p>
        <a href="/login">
            <img src="https://developers.google.com/identity/images/btn_google_signin_dark_normal_web.png" alt="Sign in with Google"/>
        </a>
        <div style="margin-top: 30px; font-size: 0.9em; color: #888; font-style: italic;">
            Login allows only sadhguru.org emails
        </div>
    </body>
    </html>
    """

def create_gradio_interface():
    """Create Gradio interface with enhanced feedback handling"""
    
    with gr.Blocks(theme=gr.themes.Soft(), title="Welcome to Sevabot", css="""
        .logout-btn { background-color: #dc2626 !important; color: white !important; }
        .sessions-list, .chat-interface { font-family: inherit !important; font-size: inherit !important; }
        .tab-nav button { font-size: 1.5em !important; font-weight: bold !important; }
        .gradio-container { height: 100vh !important; }
        .main { height: calc(100vh - 120px) !important; }
        .feedback-btn { min-height: 45px !important; padding: 10px 20px !important; }
        """) as demo:
        
        # State variables
        current_conversation_id = gr.State(None)
        last_assistant_message_id = gr.State(None)
        
        # Header
        with gr.Row():
            with gr.Column(scale=4):
                gr.Markdown("# 🙏 Sevabot")
            with gr.Column(scale=1):
                logout_btn = gr.Button("Logout", variant="stop", size="lg", elem_classes="logout-btn")
        
        gr.Markdown("<br>")
        
        # Main tabs
        with gr.Tabs():
            # Chat Tab
            with gr.TabItem("💬 Chat"):
                with gr.Row():
                    # Left sidebar - Sessions
                    with gr.Column(scale=1):
                        gr.Markdown("### Chat Sessions")
                        with gr.Row(equal_height=True):
                            with gr.Column(scale=1):
                                new_chat_btn = gr.Button("New", variant="primary", size="lg")
                            with gr.Column(scale=1):
                                delete_chat_btn = gr.Button("Delete", variant="secondary", size="lg")
                        
                        sessions_radio = gr.Radio(
                            label="Conversations",
                            choices=[],
                            value=None,
                            interactive=True,
                            show_label=False,
                            elem_classes="sessions-list"
                        )
                    
                    # Main chat area (wider)
                    with gr.Column(scale=5):
                        chatbot = gr.Chatbot(
                            label="",
                            height="70vh",
                            show_copy_button=True,
                            show_share_button=False,
                            elem_classes="chat-interface"
                        )
                        
                        # Enhanced feedback row
                        with gr.Column(visible=False) as feedback_row:
                            gr.Markdown("**Please rate this response to continue:**")
                            with gr.Row():
                                feedback_good = gr.Button("👍 Good", variant="secondary", size="lg", elem_classes="feedback-btn")
                                feedback_neutral = gr.Button("😐 Neutral", variant="secondary", size="lg", elem_classes="feedback-btn")
                                feedback_bad = gr.Button("👎 Bad", variant="secondary", size="lg", elem_classes="feedback-btn")
                            
                            # Feedback remarks with helpful footnote
                            feedback_remarks = gr.Textbox(
                                label="Additional feedback (optional)",
                                placeholder="Please provide specific feedback for neutral/bad ratings...",
                                lines=2,
                                visible=True
                            )
                            gr.Markdown("*Providing feedback for neutral/bad ratings helps improve responses*", elem_id="feedback-note")
                        
                        # Simple text input
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
                
                # Add info box about PDF requirements
                gr.Markdown("""
                **📋 File Upload Guidelines:**
                - Supported formats: `.txt`, `.md`, `.pdf`, `.docx` (max 10MB)
                - **PDF Note**: Text-searchable PDFs work best. If your PDF is scanned/image-based, convert it first using:
                  - Online OCR tools (SmallPDF, ILovePDF, etc.)
                  - Google Drive (upload → right-click → Open with Google Docs → download as PDF)
                  - Adobe Acrobat Pro (Save As → Searchable Image)
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
                        upload_btn = gr.Button("📤 Upload Files", variant="primary", size="lg")
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
                            delete_btn = gr.Button("🗑️ Delete Selected", variant="secondary", size="lg")
                            select_all_btn = gr.Button("☑️ Select All", variant="secondary", size="lg")
                        delete_status = gr.Textbox(label="Delete Progress", interactive=False, lines=6, visible=False)
                
                gr.Markdown("### 📋 Your Documents")
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh List", size="lg")
                    reindex_btn = gr.Button("🔍 Re-index Pending", size="lg")
                
                files_table = gr.Dataframe(
                    label="",
                    headers=["File Name", "Size", "Chunks", "Status", "Uploaded"],
                    datatype=["str", "str", "number", "str", "str"],
                    interactive=False,
                    wrap=True
                )
        
        # Hidden components
        action_status = gr.Textbox(visible=False)
        
        # ========== EVENT HANDLERS ==========
        
        # Initial load
        def load_initial_data():
            try:
                greeting, sessions_update = ui_service.load_initial_data()
                return sessions_update
            except Exception as e:
                print(f"Error loading initial data: {e}")
                return gr.update(choices=[])
        
        demo.load(fn=load_initial_data, outputs=[sessions_radio])
        
        # Load file data
        def safe_load_file_data():
            try:
                files = ui_service.get_file_list()
                choices = [row[0] for row in files] if files and len(files) > 0 else []
                return gr.update(value=files), gr.update(choices=choices, value=[])
            except Exception as e:
                print(f"Error loading file data: {e}")
                return gr.update(value=[]), gr.update(choices=[], value=[])

        demo.load(fn=safe_load_file_data, outputs=[files_table, selected_files])
        
        # Enhanced chat events
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
        
        # Enhanced feedback handlers with proper persistence
        def handle_feedback(feedback_type, message_id, remarks, history):
            if not message_id:
                return gr.update(interactive=True), gr.update(visible=False), history, ""
            
            try:
                # Prepare feedback data with remarks
                feedback_data = feedback_type
                if remarks and remarks.strip():
                    feedback_data = f"{feedback_type}:{remarks.strip()}"
                
                # Store feedback in database
                success = ui_service.submit_feedback(message_id, feedback_data)
                print(f"Feedback stored: {feedback_data} for message {message_id} (success: {success})")
                
                # Update chat display with feedback
                if history and len(history) > 0:
                    last_exchange = history[-1]
                    if len(last_exchange) >= 2:
                        # Create feedback display
                        feedback_emoji = {"good": "👍", "neutral": "😐", "bad": "👎"}[feedback_type]
                        feedback_display = f"{feedback_emoji} {feedback_type.title()}"
                        if remarks and remarks.strip():
                            feedback_display += f" - {remarks.strip()}"
                        
                        # Update the assistant's response with feedback
                        updated_response = last_exchange[1] + f"\n\n*[Feedback: {feedback_display}]*"
                        history[-1] = [last_exchange[0], updated_response]
                
                return gr.update(interactive=True), gr.update(visible=False), history, ""
                
            except Exception as e:
                print(f"Error handling feedback: {e}")
                return gr.update(interactive=True), gr.update(visible=False), history, ""
        
        feedback_good.click(
            fn=lambda msg_id, remarks, hist: handle_feedback("good", msg_id, remarks, hist),
            inputs=[last_assistant_message_id, feedback_remarks, chatbot],
            outputs=[message_input, feedback_row, chatbot, feedback_remarks]
        )
        
        feedback_neutral.click(
            fn=lambda msg_id, remarks, hist: handle_feedback("neutral", msg_id, remarks, hist),
            inputs=[last_assistant_message_id, feedback_remarks, chatbot],
            outputs=[message_input, feedback_row, chatbot, feedback_remarks]
        )
        
        feedback_bad.click(
            fn=lambda msg_id, remarks, hist: handle_feedback("bad", msg_id, remarks, hist),
            inputs=[last_assistant_message_id, feedback_remarks, chatbot],
            outputs=[message_input, feedback_row, chatbot, feedback_remarks]
        )
        
        # Session management
        def handle_new_chat():
            try:
                initial_history, conv_id, sessions_update, status = ui_service.create_new_chat()
                return initial_history, conv_id, sessions_update, status
            except Exception as e:
                print(f"Error in new chat: {e}")
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
        
        # File operations with better error handling
        def handle_upload_start(files):
            if not files:
                return gr.update(visible=True, value="No files selected")
            return gr.update(visible=True, value="Starting upload...")

        def handle_upload_complete(files):
            files_update, status, choices_update = ui_service.upload_files_with_progress(files)
            return files_update, gr.update(value=status), choices_update

        upload_btn.click(fn=handle_upload_start, inputs=[file_upload], outputs=[upload_status]).then(
            fn=handle_upload_complete, inputs=[file_upload], outputs=[files_table, upload_status, selected_files]
        )
        
        def handle_delete_start(selected):
            if not selected:
                return gr.update(visible=True, value="No files selected")
            return gr.update(visible=True, value="Starting deletion...")

        def handle_delete_complete(selected):
            files_update, status, choices_update = ui_service.delete_files_with_progress(selected)
            return files_update, gr.update(value=status), choices_update
        
        delete_btn.click(fn=handle_delete_start, inputs=[selected_files], outputs=[delete_status]).then(
            fn=handle_delete_complete, inputs=[selected_files], outputs=[files_table, delete_status, selected_files]
        )
        
        def select_all_files():
            files = ui_service.get_file_list()
            all_files = [row[0] for row in files] if files else []
            return gr.update(value=all_files)
        
        select_all_btn.click(fn=select_all_files, outputs=[selected_files])
        refresh_btn.click(fn=safe_load_file_data, outputs=[files_table, selected_files])
        
        def handle_reindex():
            result = ui_service.reindex_pending_files()
            files = ui_service.get_file_list()
            choices = [row[0] for row in files] if files else []
            return gr.update(value=files), gr.update(choices=choices), result
        
        reindex_btn.click(fn=handle_reindex, outputs=[files_table, selected_files, action_status])
        
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
        return RedirectResponse("/gradio")

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