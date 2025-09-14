# ui_styles.py - All UI styling and design elements

def get_favicon_link():
    """Get favicon link HTML"""
    return '<link rel="icon" href="https://isha.sadhguru.org/favicon.ico" type="image/x-icon">'

def get_isha_logo_svg():
    """Get enhanced Isha logo SVG for header"""
    return """
    <div style="display: flex; align-items: center;">
        <svg width="300" height="65" viewBox="0 0 250 60">
            <defs>
                <linearGradient id="headerLogoGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
                </linearGradient>
            </defs>
            <!-- White circle only behind Isha logo -->
            <circle 
                cx="30" cy="30" r="26" 
                fill="white" 
                stroke="url(#headerLogoGradient)" 
                stroke-width="2"
            />
            <image x="12" y="12" width="36" height="36" href="https://isha.sadhguru.org/favicon.ico"/>
            <!-- Sevabot text without background -->
            <text x="70" y="38" font-family="'Google Sans', 'Product Sans', 'Roboto', system-ui, sans-serif" font-size="28" font-weight="700" fill="url(#headerLogoGradient)" letter-spacing="1.2px">Sevabot</text>
            <circle cx="210" cy="25" r="3" fill="url(#headerLogoGradient)" opacity="0.8"/>
            <circle cx="220" cy="30" r="2.5" fill="url(#headerLogoGradient)" opacity="0.6"/>
            <circle cx="230" cy="35" r="2" fill="url(#headerLogoGradient)" opacity="0.7"/>
        </svg>
    </div>
    """

def get_landing_page_html():
    """Get complete landing page HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to Isha Sevabot</title>
        {get_favicon_link()}
        <style>
            {get_landing_page_css()}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div> 🙏 Namaskaram, Welcome to</div>
            <h1 class="title">Isha Sevabot</h1>
            
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

def get_landing_page_css():
    """Landing page CSS styles"""
    return """
        html, body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif;
            text-align: center;
            padding: 0;
            margin: 0;
            background: white;
            color: #333;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
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
    """

def get_main_app_css():
    """Main application CSS styles - cleaned and optimized"""
    return """
        /* Hide Gradio footer */
        .gradio-container .footer, .gradio-container footer, footer[data-testid="footer"], .gradio-container > div:last-child { 
            display: none !important; 
        }
        
        /* Global font family */
        * { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif !important;
            box-sizing: border-box !important;
        }

        /* Force specific row to be horizontal */
        .gradio-container .gradio-column .gradio-row:has(button) {
            display: flex !important;
            flex-direction: row !important;
            width: 100% !important;
            gap: 0.25rem !important;
        }

        .gradio-container .gradio-column .gradio-row:has(button) > * {
            flex: 1 !important;
            min-width: 0 !important;
        }
                
        /* Layout reset */
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            overflow-x: hidden !important;
        }
        
        /* Container */
        .gradio-container {
            width: 100vw !important;
            height: 100vh !important;
            margin: 0 !important;
            padding: 0.5rem !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            display: flex !important;
            flex-direction: column !important;
        }
        
        /* Text spacing */
        .gradio-container p, .gradio-container h1, .gradio-container h2, .gradio-container h3, 
        .gradio-container .markdown {
            margin: 0.5rem 0 !important;
            padding: 0.25rem !important;
        }

        /* ========== THEMED ACTION BUTTONS ========== */

        /* Gradient buttons with glow */
        .new-chat-btn {
            background: linear-gradient(135deg, #f3e8ff, #d8b4fe) !important; /* soft lilac gradient */
            color: #4c1d95 !important;  /* deep purple for contrast */
            border: none !important;
            font-size: 1rem !important; /* make emoji bigger */
            transition: all 0.3s ease !important;
        }
        .new-chat-btn:hover {
            box-shadow: 0 4px 12px rgba(216, 180, 254, 0.6) !important;
            transform: translateY(-1px) !important;
        }

        .delete-chat-btn {
            background: linear-gradient(135deg, #a855f7, #9333ea) !important;
            color: white !important;
            border: none !important;
            transition: all 0.3s ease !important;
        }
        .delete-chat-btn:hover {
            box-shadow: 0 4px 12px rgba(148, 51, 211, 0.5) !important;
            transform: translateY(-1px) !important;
        }

        .refresh-chat-btn {
            background: linear-gradient(135deg, #6d28d9, #5b21b6) !important;
            color: white !important;
            border: none !important;
            transition: all 0.3s ease !important;
        }
        .refresh-chat-btn:hover {
            box-shadow: 0 4px 12px rgba(109, 40, 217, 0.5) !important;
            transform: translateY(-1px) !important;
        }

        /* ========== TOOLTIP FIX ========== */
        .new-chat-btn::after,
        .delete-chat-btn::after,
        .refresh-chat-btn::after {
            position: absolute !important;
            top: -1.8rem !important;   /* show above instead of below */
            left: 50% !important;
            transform: translateX(-50%) !important;
            background: rgba(0,0,0,0.85) !important;
            color: white !important;
            padding: 0.25rem 0.5rem !important;
            border-radius: 4px !important;
            font-size: 0.75rem !important;
            white-space: nowrap !important;
            opacity: 0 !important;
            pointer-events: none !important;
            transition: opacity 0.2s !important;
            z-index: 10000 !important;   /* float above radios */
        }

        /* Individual tooltip labels */
        .new-chat-btn::after { content: "New Chat"; }
        .delete-chat-btn::after { content: "Delete Chat"; }
        .refresh-chat-btn::after { content: "Refresh"; }

        /* Show on hover */
        .new-chat-btn:hover::after,
        .delete-chat-btn:hover::after,
        .refresh-chat-btn:hover::after {
            opacity: 1 !important;
        }

        
        /* Chat messages spacing */
        .chatbot .message, .chatbot .message-wrap {
            margin: 0.1rem 0 !important;
            padding: 0.3rem 0.5rem !important;
            line-height: 1.3 !important;
        }
        
        /* Header and main areas */
        .gradio-container > div:first-child {
            padding: 0.5rem !important;
            flex-shrink: 0 !important;
        }
        
        .gradio-container > div:nth-child(2) {
            flex: 1 !important;
            padding: 0 0.5rem !important;
        }
        
        /* Chat layout spacing */
        .gradio-tabs .tabitem .gradio-row {
            gap: 1rem !important;
        }
        
        /* Logo styling */
        .sevabot-logo { 
            height: 4rem !important;
            display: flex !important;
            align-items: center !important;
            overflow: hidden !important;
        }
        
        .sevabot-logo svg {
            width: 16rem !important;
            height: 4rem !important;
            flex-shrink: 0 !important;
        }
        
        /* Button styles */
        .send-btn-compact, .send-btn {
            background-color: #dc2626 !important;
            color: white !important;
            font-weight: 500 !important;
            min-width: 60px !important;
            max-width: 80px !important;
            padding: 0.5rem !important;
            font-size: 0.875rem !important;
        }
        
        .logout-btn { 
            background-color: #dc2626 !important; 
            color: white !important;
            min-width: 5rem !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.875rem !important;
        }
        
        /* Notifications */
        .notification {
            position: fixed !important;
            top: 1rem !important;
            right: 1rem !important;
            background: #10b981 !important;
            color: white !important;
            padding: 0.75rem 1.25rem !important;
            border-radius: 0.5rem !important;
            box-shadow: 0 0.25rem 0.75rem rgba(0,0,0,0.15) !important;
            z-index: 1000 !important;
            font-weight: 600 !important;
            animation: fadeInOut 5s ease-in-out forwards !important;
        }

        @keyframes fadeInOut {
            0% { opacity: 0; transform: translateX(100%); }
            10% { opacity: 1; transform: translateX(0); }
            90% { opacity: 1; transform: translateX(0); }
            100% { opacity: 0; transform: translateX(100%); }
        }
        
        /* Feedback buttons */
        .feedback-btn { 
            min-height: 2.5rem !important; 
            padding: 0.625rem 1.25rem !important; 
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            margin: 0.25rem !important;
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
        
        /* Section backgrounds */
        .admin-section, .files-section {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%) !important;
            border: 1px solid rgba(102, 126, 234, 0.2) !important;
            border-radius: 0.75rem !important;
            padding: 1rem !important;
            margin: 0.5rem 0 !important;
        }
        
        .spoc-section {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(251, 191, 36, 0.1) 100%) !important;
            border: 1px solid rgba(245, 158, 11, 0.2) !important;
            border-radius: 0.75rem !important;
            padding: 1rem !important;
            margin: 0.5rem 0 !important;
        }
        
        /* Copyright footer */
        .copyright-footer {
            text-align: center !important;
            color: #9ca3af !important;
            font-size: 0.875rem !important;
            padding: 1rem 0.5rem !important;
            margin-top: auto !important;
            flex-shrink: 0 !important;
            background: white !important;
        }
        
        /* Scrollbar */
        html { scrollbar-gutter: stable; }
        
        /* Mobile */
        @media (max-width: 48rem) {
            .gradio-container { padding: 0.25rem !important; }
            .sevabot-logo svg { width: 12rem !important; height: 3rem !important; }
        }
    """