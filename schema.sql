CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    email_verified INTEGER DEFAULT 0, -- 1 = true, 0 = false
    password TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    token TEXT
);

CREATE TABLE IF NOT EXISTS cryptocurrencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,  -- e.g. BTCUSDT
    name TEXT NOT NULL            -- e.g. Bitcoin
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    crypto_id INTEGER NOT NULL,
    condition_type TEXT NOT NULL CHECK (condition_type IN ('above', 'below', 'percent_change')),
    target_value REAL NOT NULL,
    duration_minutes INTEGER DEFAULT NULL, -- only for percent_change
    is_active INTEGER DEFAULT 1,           -- 1 = active, 0 = disabled
    last_triggered DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (crypto_id) REFERENCES cryptocurrencies(id)
);