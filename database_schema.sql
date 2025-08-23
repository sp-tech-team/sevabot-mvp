-- Updated Supabase Database Schema for Sevabot
-- Run this in your Supabase SQL Editor

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  avatar_url TEXT,
  provider TEXT DEFAULT 'google',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB
);

-- 2. Conversations table (Sessions)
CREATE TABLE IF NOT EXISTS conversations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Messages table with feedback
CREATE TABLE IF NOT EXISTS messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  feedback TEXT CHECK (feedback IN ('good', 'neutral', 'bad')) DEFAULT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. User documents table (for file tracking)
CREATE TABLE IF NOT EXISTS user_documents (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size BIGINT NOT NULL,
  file_hash TEXT NOT NULL,
  chunks_count INTEGER NOT NULL DEFAULT 0,
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, file_name)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_feedback ON messages(feedback);
CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_documents_uploaded_at ON user_documents(uploaded_at DESC);

-- -- Row Level Security (RLS) policies
-- ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_documents ENABLE ROW LEVEL SECURITY;

-- -- Policies for conversations
-- CREATE POLICY "Users can view own conversations" ON conversations FOR SELECT USING (user_id = current_setting('request.jwt.claims')::json->>'email');
-- CREATE POLICY "Users can insert own conversations" ON conversations FOR INSERT WITH CHECK (user_id = current_setting('request.jwt.claims')::json->>'email');
-- CREATE POLICY "Users can update own conversations" ON conversations FOR UPDATE USING (user_id = current_setting('request.jwt.claims')::json->>'email');
-- CREATE POLICY "Users can delete own conversations" ON conversations FOR DELETE USING (user_id = current_setting('request.jwt.claims')::json->>'email');

-- -- Policies for messages  
-- CREATE POLICY "Users can view own messages" ON messages FOR SELECT USING (
--   conversation_id IN (
--     SELECT id FROM conversations WHERE user_id = current_setting('request.jwt.claims')::json->>'email'
--   )
-- );
-- CREATE POLICY "Users can insert own messages" ON messages FOR INSERT WITH CHECK (
--   conversation_id IN (
--     SELECT id FROM conversations WHERE user_id = current_setting('request.jwt.claims')::json->>'email'
--   )
-- );
-- CREATE POLICY "Users can update own messages" ON messages FOR UPDATE USING (
--   conversation_id IN (
--     SELECT id FROM conversations WHERE user_id = current_setting('request.jwt.claims')::json->>'email'
--   )
-- );

-- -- Policies for user documents
-- CREATE POLICY "Users can view own documents" ON user_documents FOR SELECT USING (user_id = current_setting('request.jwt.claims')::json->>'email');
-- CREATE POLICY "Users can insert own documents" ON user_documents FOR INSERT WITH CHECK (user_id = current_setting('request.jwt.claims')::json->>'email');
-- CREATE POLICY "Users can update own documents" ON user_documents FOR UPDATE USING (user_id = current_setting('request.jwt.claims')::json->>'email');
-- CREATE POLICY "Users can delete own documents" ON user_documents FOR DELETE USING (user_id = current_setting('request.jwt.claims')::json->>'email');