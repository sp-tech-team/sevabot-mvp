-- Complete Database Schema for SEVABOT with 3-tier role system and common knowledge repository

-- Users table (existing, but make sure it has role column)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'spoc', 'user')),
    avatar_url TEXT,
    provider VARCHAR(50) DEFAULT 'google',
    last_login TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations table (existing)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(email) ON DELETE CASCADE
);

-- Messages table (existing)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Common knowledge documents table (NEW)
CREATE TABLE IF NOT EXISTS common_knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name VARCHAR(255) NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(255),
    chunks_count INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    uploaded_by VARCHAR(255) NOT NULL,
    indexed_at TIMESTAMP,
    is_common_knowledge BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (uploaded_by) REFERENCES users(email) ON DELETE SET NULL
);

-- SPOC assignments table (NEW)
CREATE TABLE IF NOT EXISTS spoc_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spoc_email VARCHAR(255) NOT NULL,
    assigned_user_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(spoc_email, assigned_user_email),
    FOREIGN KEY (spoc_email) REFERENCES users(email) ON DELETE CASCADE,
    FOREIGN KEY (assigned_user_email) REFERENCES users(email) ON DELETE CASCADE
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_common_knowledge_uploaded_at ON common_knowledge_documents(uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_spoc_assignments_spoc ON spoc_assignments(spoc_email);
CREATE INDEX IF NOT EXISTS idx_spoc_assignments_user ON spoc_assignments(assigned_user_email);

-- Enable Row Level Security (optional, for additional security)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE common_knowledge_documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE spoc_assignments ENABLE ROW LEVEL SECURITY;