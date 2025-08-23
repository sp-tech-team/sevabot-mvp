# Sevabot - AI Document Assistant

A multi-user RAG (Retrieval-Augmented Generation) system that allows users to upload documents and ask questions about them through a conversational interface.

## ✨ Features

- **Multi-user support** with Google OAuth authentication
- **Document upload** support (.txt, .md, .pdf, .docx)
- **Conversational chat** with document context
- **Source citation** in AI responses
- **Feedback system** for improving responses
- **Session management** with conversation history
- **File management** with indexing status

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python
- **Frontend**: Gradio
- **Database**: Supabase (PostgreSQL)
- **Vector Store**: ChromaDB
- **LLM**: OpenAI GPT-4
- **Authentication**: Google OAuth via Supabase

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Supabase account
- OpenAI API key
- Google OAuth configured in Supabase

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd sevabot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Set up database**
- Create a Supabase project
- Run the SQL from `database_schema.sql` in Supabase SQL Editor

5. **Run the application**
```bash
python main.py
```

6. **Access the app**
- Open http://localhost:8000
- Sign in with your @sadhguru.org Google account

## 📝 Environment Variables

Required variables (add to `.env`):
```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
OPENAI_API_KEY=your_openai_api_key
COOKIE_SECRET=your_secure_random_string
```

Optional (has defaults):
```bash
ALLOWED_DOMAIN=sadhguru.org
CHAT_MODEL=gpt-4o
TOP_K=8
```

## 📊 Usage

1. **Upload Documents**: Go to File Manager tab and upload your documents
2. **Chat**: Ask questions about your uploaded documents
3. **Feedback**: Rate responses to improve the system
4. **Sessions**: Manage multiple conversation threads

## 🔒 Security

- Domain-restricted authentication (@sadhguru.org only)
- User-isolated document storage
- Secure session management
- Environment-based configuration

## 📁 Project Structure

```
sevabot/
├── main.py              # FastAPI application entry point
├── ui.py                # Gradio interface
├── ui_service.py        # UI business logic
├── auth.py              # Authentication handling
├── chat_service.py      # Chat and conversation management
├── rag_service.py       # RAG and vector storage
├── file_service.py      # File upload and management
├── config.py            # Configuration management
├── constants.py         # Application constants
├── database_schema.sql  # Database schema
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

Private repository - All rights reserved.