-- Add Watchlist Feature
-- This table allows users to bookmark movies for later viewing

CREATE TABLE IF NOT EXISTS WATCHLIST (
    userId INT NOT NULL,
    movieId INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
    PRIMARY KEY (userId, movieId),
    FOREIGN KEY (userId) REFERENCES USERS(userId) ON DELETE CASCADE,
    FOREIGN KEY (movieId) REFERENCES MOVIES(movieId) ON DELETE CASCADE,
    INDEX idx_user_added (userId, added_at DESC),
    INDEX idx_movie (movieId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Note: Run this SQL file to add watchlist support to your database
-- mysql -u root -p movies_db < 6_create_watchlist.sql
