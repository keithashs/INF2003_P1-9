-- ============================================================================
-- RENUMBER USER IDs SEQUENTIALLY (1, 2, 3, ... 675)
-- This script fixes gaps in userId sequence and updates all foreign keys
-- ============================================================================

USE movies_db;

-- Step 1: Create a temporary mapping table
DROP TABLE IF EXISTS user_id_mapping;
CREATE TEMPORARY TABLE user_id_mapping (
    old_userId INT,
    new_userId INT,
    PRIMARY KEY (old_userId),
    INDEX (new_userId)
);

-- Step 2: Generate sequential mapping for all existing users
SET @new_id = 0;
INSERT INTO user_id_mapping (old_userId, new_userId)
SELECT userId, (@new_id := @new_id + 1) as new_userId
FROM users
ORDER BY userId;

-- Step 3: Show the mapping (sample)
SELECT 'User ID Mapping (Sample):' as info;
SELECT old_userId, new_userId 
FROM user_id_mapping 
WHERE old_userId IN (1, 2, 671, 1237, 1238, 1239, 1240)
ORDER BY old_userId;

-- Step 4: Create backup table for users
DROP TABLE IF EXISTS users_backup;
CREATE TABLE users_backup AS SELECT * FROM users;
SELECT 'Backup created: users_backup' as info;

-- Step 5: Disable foreign key checks temporarily
SET FOREIGN_KEY_CHECKS = 0;

-- Step 6: Update ratings table with new user IDs
UPDATE ratings r
INNER JOIN user_id_mapping m ON r.userId = m.old_userId
SET r.userId = m.new_userId;
SELECT 'Updated ratings table' as info;

-- Step 7: Update rating_locks table with new user IDs
UPDATE rating_locks rl
INNER JOIN user_id_mapping m ON rl.userId = m.old_userId
SET rl.userId = m.new_userId;
SELECT 'Updated rating_locks table' as info;

-- Step 8: Create a new users table with new IDs
CREATE TABLE users_new LIKE users;

-- Step 9: Copy users with new IDs
INSERT INTO users_new (userId, username, email, password_hash, role, created_at)
SELECT 
    m.new_userId,
    u.username,
    u.email,
    u.password_hash,
    u.role,
    u.created_at
FROM users u
INNER JOIN user_id_mapping m ON u.userId = m.old_userId
ORDER BY m.new_userId;

-- Step 10: Drop old users table and rename new one
DROP TABLE users;
RENAME TABLE users_new TO users;
SELECT 'Users table renumbered' as info;

-- Step 11: Reset AUTO_INCREMENT to next available ID
ALTER TABLE users AUTO_INCREMENT = 676;
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
FROM users;

-- Step 14: Show sample of renumbered users
SELECT 'Sample of Renumbered Users:' as info;
SELECT userId, username, email, role 
FROM users 
WHERE userId IN (1, 2, 100, 200, 300, 400, 500, 600, 670, 671, 672, 673, 674, 675)
ORDER BY userId;

-- Step 15: Verify ratings are still linked correctly
SELECT 'Ratings Count by User (Sample):' as info;
SELECT 
    u.userId,
    u.username,
    COUNT(r.rating) as rating_count
FROM users u
LEFT JOIN ratings r ON u.userId = r.userId
WHERE u.userId IN (1, 2, 100, 500, 675)
GROUP BY u.userId, u.username
ORDER BY u.userId;

-- Step 16: Check for any orphaned ratings (should be 0)
SELECT 'Orphaned Ratings Check:' as info;
SELECT COUNT(*) as orphaned_ratings
FROM ratings r
LEFT JOIN users u ON r.userId = u.userId
WHERE u.userId IS NULL;

SELECT '============================================' as info;
SELECT 'RENUMBERING COMPLETE!' as info;
SELECT 'All user IDs are now sequential: 1-675' as info;
SELECT 'Backup saved in: users_backup table' as info;
SELECT '============================================' as info;
