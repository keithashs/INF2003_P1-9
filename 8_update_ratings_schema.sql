-- ============================================================
-- Migration Script: Update RATINGS table to allow NULL userId
-- This preserves ratings when users are deleted, maintaining
-- accurate movie averages and vote counts
-- ============================================================

USE movies_db;

-- Step 1: Modify userId to allow NULL
ALTER TABLE RATINGS MODIFY COLUMN userId INT NULL;

-- Step 2: Drop the old primary key (includes userId which can now be NULL)
ALTER TABLE RATINGS DROP PRIMARY KEY;

-- Step 3: Add new primary key without userId (since userId can be NULL)
-- Primary key only on movieId and timestamp
ALTER TABLE RATINGS ADD PRIMARY KEY (movieId, timestamp);

-- Step 4: Add index on userId for better query performance with non-NULL values
CREATE INDEX IF NOT EXISTS idx_userId ON RATINGS(userId);

-- Step 5: Add composite index for user-movie-timestamp queries
CREATE INDEX IF NOT EXISTS idx_user_movie_rating ON RATINGS(userId, movieId, timestamp);

-- Verify changes
SELECT 
    'Schema updated successfully!' AS Status,
    'userId can now be NULL in RATINGS table' AS ChangeDescription,
    'User deletion will preserve ratings' AS Benefit;

-- Show the updated table structure
DESCRIBE RATINGS;
