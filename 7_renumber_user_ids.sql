-- ============================================================================
-- RENUMBER USER IDs SEQUENTIALLY (1, 2, 3, ... 675)
-- This script fixes gaps in userId sequence and updates all foreign keys
-- ============================================================================

USE movies_db;

-- Disable safe update mode
SET SQL_SAFE_UPDATES = 0;

-- Step 1: Create a temporary mapping table
DROP TABLE IF EXISTS user_id_mapping;
CREATE TEMPORARY TABLE user_id_mapping (
    old_userId INT,
    new_userId INT,
    PRIMARY KEY (old_userId),
    INDEX (new_userId)
);

-- Step 2: Generate sequential mapping for all existing USERS
SET @new_id = 0;
INSERT INTO user_id_mapping (old_userId, new_userId)
SELECT userId, (@new_id := @new_id + 1) as new_userId
FROM USERS
ORDER BY userId;

-- Step 3: Show the mapping (sample)
SELECT 'User ID Mapping (Sample):' as info;
SELECT old_userId, new_userId 
FROM user_id_mapping 
WHERE old_userId IN (1, 2, 671, 1237, 1238, 1239, 1240)
ORDER BY old_userId;

-- Step 4: Create backup table for USERS
DROP TABLE IF EXISTS users_backup;
CREATE TABLE users_backup AS SELECT * FROM USERS;
SELECT 'Backup created: users_backup' as info;

-- Step 5: Disable foreign key checks temporarily
SET FOREIGN_KEY_CHECKS = 0;

-- Step 6: Update RATINGS table with new user IDs
UPDATE RATINGS r
INNER JOIN user_id_mapping m ON r.userId = m.old_userId
SET r.userId = m.new_userId;
SELECT 'Updated RATINGS table' as info;

-- Step 7: Update rating_locks table with new user IDs
UPDATE rating_locks rl
INNER JOIN user_id_mapping m ON rl.userId = m.old_userId
SET rl.userId = m.new_userId;
SELECT 'Updated rating_locks table' as info;

-- Step 8: Create a new USERS table with new IDs
CREATE TABLE users_new LIKE USERS;

-- Step 9: Copy USERS with new IDs
INSERT INTO users_new (userId, username, email, password_hash, role, created_at)
SELECT 
    m.new_userId,
    u.username,
    u.email,
    u.password_hash,
    u.role,
    u.created_at
FROM USERS u
INNER JOIN user_id_mapping m ON u.userId = m.old_userId
ORDER BY m.new_userId;

-- Step 10: Drop old USERS table and rename new one
DROP TABLE USERS;
RENAME TABLE users_new TO USERS;
SELECT 'USERS table renumbered' as info;

-- Step 11: Reset AUTO_INCREMENT to next available ID
ALTER TABLE USERS AUTO_INCREMENT = 676;
SELECT 'AUTO_INCREMENT reset to 676' as info;

-- Step 12: Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Step 13: Verify the results
SELECT 'Verification Results:' as info;
SELECT 
    MIN(userId) as min_userId,
    MAX(userId) as max_userId,
    COUNT(*) as total_users,
    MAX(userId) - MIN(userId) + 1 as expected_count,
    MAX(userId) - MIN(userId) + 1 - COUNT(*) as gaps
FROM USERS;

-- Step 14: Show sample of renumbered USERS
SELECT 'Sample of Renumbered USERS:' as info;
SELECT userId, username, email, role 
FROM USERS 
WHERE userId IN (1, 2, 100, 200, 300, 400, 500, 600, 670, 671, 672, 673, 674, 675)
ORDER BY userId;

-- Step 15: Verify RATINGS are still linked correctly
SELECT 'RATINGS Count by User (Sample):' as info;
SELECT 
    u.userId,
    u.username,
    COUNT(r.rating) as rating_count
FROM USERS u
LEFT JOIN RATINGS r ON u.userId = r.userId
WHERE u.userId IN (1, 2, 100, 500, 675)
GROUP BY u.userId, u.username
ORDER BY u.userId;

-- Step 16: Check for any orphaned RATINGS (should be 0)
SELECT 'Orphaned RATINGS Check:' as info;
SELECT COUNT(*) as orphaned_ratings
FROM RATINGS r
LEFT JOIN USERS u ON r.userId = u.userId
WHERE u.userId IS NULL;

SELECT '============================================' as info;
SELECT 'RENUMBERING COMPLETE!' as info;
SELECT 'All user IDs are now sequential: 1-675' as info;
SELECT 'Backup saved in: users_backup table' as info;
SELECT '============================================' as info;

-- ===================================================================
-- TRANSFER ADMIN RATINGS TO ANOTHER USER
-- ===================================================================
-- This section transfers all RATINGS made by admin (userId=1) 
-- to another user to keep admin account clean (no RATINGS).
--
-- SAFETY CHECKS:
-- 1. Check how many RATINGS admin has
-- 2. Verify target user exists
-- 3. Check for conflicts (if target user already rated same movies)
-- 4. Perform the transfer
-- ===================================================================

SELECT '' as info;
SELECT '============================================' as info;
SELECT 'STARTING ADMIN RATINGS TRANSFER' as info;
SELECT '============================================' as info;

-- Step 1: Check admin's RATINGS
SELECT 'Admin (userId=1) currently has these RATINGS:' AS info;
SELECT 
    r.userId,
    r.movieId,
    m.title,
    r.rating,
    FROM_UNIXTIME(r.timestamp) AS rated_at
FROM RATINGS r
INNER JOIN movies m ON r.movieId = m.movieId
WHERE r.userId = 1
ORDER BY r.timestamp DESC;

SELECT COUNT(*) AS admin_rating_count 
FROM RATINGS 
WHERE userId = 1;

-- Step 2: Choose a target user (MODIFY THIS!)
-- Option A: Transfer to user ID 2
SET @target_user_id = 2;

-- Option B: Create a new user for these RATINGS
-- INSERT INTO USERS (userId, username, email, role, password_hash)
-- VALUES (999, 'movie_reviewer', 'reviewer@example.com', 'user', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aqaaf6V.Ps2G');
-- SET @target_user_id = 999;

-- Step 3: Verify target user exists
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN CONCAT('Target user ', @target_user_id, ' exists')
        ELSE CONCAT('ERROR: Target user ', @target_user_id, ' does NOT exist!')
    END AS user_check
FROM USERS 
WHERE userId = @target_user_id;

-- Step 4: Check for conflicts (movies both USERS rated)
SELECT 'Potential conflicts (both USERS rated same movies):' AS info;
SELECT 
    admin_r.movieId,
    m.title,
    admin_r.rating AS admin_rating,
    target_r.rating AS target_user_rating
FROM RATINGS admin_r
INNER JOIN RATINGS target_r ON admin_r.movieId = target_r.movieId
INNER JOIN movies m ON admin_r.movieId = m.movieId
WHERE admin_r.userId = 1 
  AND target_r.userId = @target_user_id;

-- Step 5: Handle conflicts - Delete target user's RATINGS for conflicting movies
-- (We'll keep admin's RATINGS and transfer them)
SELECT 'Deleting conflicting RATINGS from target user...' AS info;
DELETE FROM RATINGS
WHERE userId = @target_user_id
  AND movieId IN (
      SELECT movieId 
      FROM RATINGS 
      WHERE userId = 1
  );

-- Step 6: Transfer all admin RATINGS to target user
SELECT 'Transferring admin RATINGS to target user...' AS info;
UPDATE RATINGS
SET userId = @target_user_id
WHERE userId = 1;

-- Step 7: Verify the transfer
SELECT 'Admin RATINGS after transfer:' AS info;
SELECT COUNT(*) AS admin_rating_count 
FROM RATINGS 
WHERE userId = 1;

SELECT CONCAT('Target user (', @target_user_id, ') RATINGS after transfer:') AS info;
SELECT COUNT(*) AS target_user_rating_count 
FROM RATINGS 
WHERE userId = @target_user_id;

-- Step 8: Show sample of transferred RATINGS
SELECT 'Sample of transferred RATINGS:' AS info;
SELECT 
    r.userId,
    r.movieId,
    m.title,
    r.rating,
    FROM_UNIXTIME(r.timestamp) AS rated_at
FROM RATINGS r
INNER JOIN movies m ON r.movieId = m.movieId
WHERE r.userId = @target_user_id
ORDER BY r.timestamp DESC
LIMIT 10;

SELECT '============================================' as info;
SELECT 'TRANSFER COMPLETE!' as info;
SELECT 'Admin account now has 0 RATINGS.' as info;
SELECT '============================================' as info;

-- Re-enable safe update mode
SET SQL_SAFE_UPDATES = 1;
