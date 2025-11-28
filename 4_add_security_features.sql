-- Add security and transaction handling features
-- Run this script to add user authentication and rating locks

USE movies_db;

-- Add authentication columns only if they don't exist
ALTER TABLE USERS 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(64) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS role ENUM('user', 'admin') DEFAULT 'user';

-- Create index on username for faster login lookups
CREATE INDEX IF NOT EXISTS idx_username ON USERS(username);

-- Create RATING_LOCKS table for transaction handling
CREATE TABLE IF NOT EXISTS RATING_LOCKS (
    userId INT NOT NULL,
    movieId INT NOT NULL,
    locked_by VARCHAR(100) NOT NULL,
    locked_at BIGINT NOT NULL,
    PRIMARY KEY (userId, movieId),
    FOREIGN KEY (userId) REFERENCES USERS(userId) ON DELETE CASCADE,
    FOREIGN KEY (movieId) REFERENCES MOVIES(movieId) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Disable safe update mode to allow updates without key column in WHERE clause
SET SQL_SAFE_UPDATES = 0;

-- Set default passwords for existing users (password: "password123")
-- Hash: ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f
UPDATE USERS 
SET password_hash = 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
    role = 'user'
WHERE password_hash IS NULL;

-- Create admin user (userId=1)
UPDATE USERS
SET password_hash = 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
    role = 'admin',
    username = 'admin',
    email = 'admin@moviedb.com'
WHERE userId = 1;

-- Create test regular user (userId=2)
UPDATE USERS
SET password_hash = 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
    role = 'user',
    username = 'testuser',
    email = 'test@moviedb.com'
WHERE userId = 2;

-- Re-enable safe update mode
SET SQL_SAFE_UPDATES = 1;

-- Show summary
SELECT 'Security features added successfully' AS Status;
SELECT COUNT(*) AS TotalUsers, 
       SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) AS Admins,
       SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) AS RegularUsers
FROM USERS;
