-- Migration: 0000_initial_schema.sql
-- Description: Sets up the initial tables for users, reports, and signals.

-- Drop tables if they exist for a clean slate on re-runs during development
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS signals;

-- Create the users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user', 'admin')), -- Role can only be 'user' or 'admin'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create the reports table
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL, -- Will store HTML content from the rich-text editor
    author_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE -- Link to the user who wrote it
);

-- Create the signals table
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_content TEXT NOT NULL, -- The original text from the TradingView webhook
    parsed_content TEXT, -- Storing the parsed data as a JSON string
    received_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_reports_author_id ON reports(author_id);
