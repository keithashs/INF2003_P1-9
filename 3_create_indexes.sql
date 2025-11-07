-- ============================================================
-- INF2003 Movie Database - Indexing and Optimization Script
-- Creates indexes for improved query performance
-- (ADVANCED FEATURE for Final Report!)
-- ============================================================

USE movies_db;

-- ============================================================
-- PART 1: Performance Analysis BEFORE Indexing
-- ============================================================

-- Check current table sizes
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS 'Size (MB)',
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS 'Index Size (MB)'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'movies_db'
    AND TABLE_NAME IN ('USERS', 'MOVIES', 'RATINGS', 'LINKS')
ORDER BY TABLE_NAME;

-- Test Query 1: Find movies with high ratings (WITHOUT optimization)
-- Run this and note the execution time!
EXPLAIN
SELECT m.movieId, m.title, AVG(r.rating) as avg_rating
FROM MOVIES m
JOIN RATINGS r ON m.movieId = r.movieId
WHERE r.rating >= 4.0
GROUP BY m.movieId, m.title
HAVING AVG(r.rating) >= 4.5
ORDER BY avg_rating DESC
LIMIT 10;

-- ============================================================
-- PART 2: Create Additional Indexes
-- (These supplement the indexes already created in schema)
-- ============================================================

-- Index for rating-based filtering (already exists in schema)
-- CREATE INDEX idx_ratings_rating ON RATINGS(rating);

-- Composite index for JOIN + filter operations
CREATE INDEX idx_ratings_movie_rating_composite 
ON RATINGS(movieId, rating) 
COMMENT 'Optimizes queries filtering by movie and rating';

-- Index for timestamp-based queries (e.g., "ratings in 2020")
CREATE INDEX idx_ratings_timestamp 
ON RATINGS(timestamp)
COMMENT 'Optimizes time-based filtering';

-- Index for user activity queries
CREATE INDEX idx_ratings_user_timestamp 
ON RATINGS(userId, timestamp)
COMMENT 'Optimizes user rating history queries';

-- Full-text search index on movie titles (ADVANCED!)
ALTER TABLE MOVIES ADD FULLTEXT INDEX idx_title_fulltext (title)
COMMENT 'Enables full-text search on movie titles';

-- ============================================================
-- PART 3: Test Queries AFTER Indexing
-- ============================================================

-- Test Query 1 again: Compare execution plan
EXPLAIN
SELECT m.movieId, m.title, AVG(r.rating) as avg_rating
FROM MOVIES m
JOIN RATINGS r ON m.movieId = r.movieId
WHERE r.rating >= 4.0
GROUP BY m.movieId, m.title
HAVING AVG(r.rating) >= 4.5
ORDER BY avg_rating DESC
LIMIT 10;

-- Test Query 2: Full-text search on titles
SELECT movieId, title
FROM MOVIES
WHERE MATCH(title) AGAINST('star wars' IN NATURAL LANGUAGE MODE)
LIMIT 10;

-- ============================================================
-- PART 4: Analyze Index Usage
-- ============================================================

-- Show all indexes on RATINGS table
SHOW INDEXES FROM RATINGS;

-- Show index cardinality (uniqueness)
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    SEQ_IN_INDEX,
    COLUMN_NAME,
    CARDINALITY,
    INDEX_TYPE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'movies_db'
    AND TABLE_NAME = 'RATINGS'
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- ============================================================
-- PART 5: Optimization Tips for Final Report
-- ============================================================

/*
🎯 FOR YOUR FINAL REPORT, INCLUDE:

1. **Index Strategy**
   - Show index creation commands
   - Explain WHY each index was created
   
2. **Performance Comparison**
   - Run queries with and without indexes
   - Measure execution time using EXPLAIN or actual timing
   - Create a table showing improvements:
   
   | Query Type               | Before Index | After Index | Improvement |
   |-------------------------|--------------|-------------|-------------|
   | JOIN movies + ratings   | 2.3s         | 0.4s        | 82%         |
   | Filter rating >= 4.0    | 1.8s         | 0.2s        | 89%         |
   | Full-text search        | 0.8s         | 0.05s       | 94%         |

3. **EXPLAIN Analysis**
   - Show EXPLAIN output before and after
   - Highlight differences (type: ALL vs ref)
   
4. **Trade-offs Discussion**
   - Indexes speed up SELECT but slow down INSERT/UPDATE
   - Index size increases database storage
   - Too many indexes can hurt performance
*/

-- ============================================================
-- PART 6: Maintenance Queries
-- ============================================================

-- Analyze tables to update index statistics
ANALYZE TABLE USERS, MOVIES, RATINGS, LINKS;

-- Optimize tables to defragment and reclaim space
OPTIMIZE TABLE USERS, MOVIES, RATINGS, LINKS;

-- ============================================================
-- PART 7: Monitoring Queries
-- ============================================================

-- Find slow queries (if slow query log is enabled)
-- You can enable it with: SET GLOBAL slow_query_log = 'ON';

-- Show current index usage statistics
SELECT 
    OBJECT_SCHEMA,
    OBJECT_NAME,
    INDEX_NAME,
    COUNT_STAR as 'Times Used',
    ROUND(SUM_TIMER_WAIT/1000000000000, 2) as 'Total Time (s)'
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE OBJECT_SCHEMA = 'movies_db'
    AND INDEX_NAME IS NOT NULL
ORDER BY COUNT_STAR DESC
LIMIT 10;

-- ============================================================
-- PART 8: Example Performance Testing Queries
-- ============================================================

-- Query 1: Top-rated movies with min 50 ratings
SELECT 
    m.title,
    COUNT(r.rating) as rating_count,
    ROUND(AVG(r.rating), 2) as avg_rating
FROM MOVIES m
JOIN RATINGS r ON m.movieId = r.movieId
GROUP BY m.movieId, m.title
HAVING rating_count >= 50
ORDER BY avg_rating DESC, rating_count DESC
LIMIT 20;

-- Query 2: Find users who gave high ratings (avg > 4.0)
SELECT 
    u.userId,
    COUNT(r.rating) as ratings_given,
    ROUND(AVG(r.rating), 2) as avg_rating_given
FROM USERS u
JOIN RATINGS r ON u.userId = r.userId
GROUP BY u.userId
HAVING avg_rating_given > 4.0
ORDER BY ratings_given DESC
LIMIT 10;

-- Query 3: Movies rated in a specific year (using timestamp)
-- Timestamp 1546300800 = 2019-01-01, 1577836800 = 2020-01-01
SELECT 
    m.title,
    COUNT(r.rating) as ratings_count,
    ROUND(AVG(r.rating), 2) as avg_rating
FROM MOVIES m
JOIN RATINGS r ON m.movieId = r.movieId
WHERE r.timestamp BETWEEN 1546300800 AND 1577836800
GROUP BY m.movieId, m.title
ORDER BY ratings_count DESC
LIMIT 10;

-- Query 4: Find movies with BOTH high rating AND many reviews
SELECT 
    m.title,
    m.release_date,
    COUNT(r.rating) as rating_count,
    ROUND(AVG(r.rating), 2) as avg_rating
FROM MOVIES m
JOIN RATINGS r ON m.movieId = r.movieId
WHERE r.rating >= 4.0
GROUP BY m.movieId, m.title, m.release_date
HAVING rating_count >= 100 AND avg_rating >= 4.5
ORDER BY avg_rating DESC, rating_count DESC;

-- Query 5: User rating history (for a specific user)
SELECT 
    m.title,
    r.rating,
    FROM_UNIXTIME(r.timestamp) as rated_at
FROM RATINGS r
JOIN MOVIES m ON r.movieId = m.movieId
WHERE r.userId = 1
ORDER BY r.timestamp DESC
LIMIT 20;

SHOW WARNINGS;
