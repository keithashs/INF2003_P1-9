-- ============================================================================
-- CLEAN TEST ACCOUNTS
-- This script ensures admin and testuser accounts have clean profiles
-- Run this after 7_renumber_user_ids.sql
-- ============================================================================

USE movies_db;

-- Disable safe update mode
SET SQL_SAFE_UPDATES = 0;

-- ============================================================
-- STEP 1: Delete any ratings belonging to admin (userId=1)
-- Admin account should have NO ratings for testing purposes
-- ============================================================
SELECT 'Cleaning admin account (userId=1)...' AS info;
SELECT COUNT(*) AS admin_ratings_before FROM ratings WHERE userId = 1;

DELETE FROM ratings WHERE userId = 1;

SELECT COUNT(*) AS admin_ratings_after FROM ratings WHERE userId = 1;
SELECT 'Admin account cleaned - 0 ratings' AS status;

-- ============================================================
-- STEP 2: Delete any ratings belonging to testuser (userId=2)
-- testuser account should have NO ratings for testing purposes
-- ============================================================
SELECT 'Cleaning testuser account (userId=2)...' AS info;
SELECT COUNT(*) AS testuser_ratings_before FROM ratings WHERE userId = 2;

DELETE FROM ratings WHERE userId = 2;

SELECT COUNT(*) AS testuser_ratings_after FROM ratings WHERE userId = 2;
SELECT 'testuser account cleaned - 0 ratings' AS status;

-- ============================================================
-- STEP 3: Verify admin and testuser have correct credentials
-- ============================================================
SELECT 'Verifying test accounts...' AS info;
SELECT 
    userId,
    username,
    email,
    role,
    CASE 
        WHEN password_hash = 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f' 
        THEN 'password123'
        ELSE 'custom'
    END AS password_status
FROM USERS 
WHERE userId IN (1, 2);

-- ============================================================
-- STEP 4: Show summary
-- ============================================================
SELECT '============================================' AS info;
SELECT 'TEST ACCOUNTS CLEANED SUCCESSFULLY!' AS info;
SELECT '============================================' AS info;
SELECT 'admin (userId=1): 0 ratings, role=admin' AS account_status
UNION ALL
SELECT 'testuser (userId=2): 0 ratings, role=user' AS account_status;
SELECT 'Both accounts use password: password123' AS info;

-- Re-enable safe update mode
SET SQL_SAFE_UPDATES = 1;
