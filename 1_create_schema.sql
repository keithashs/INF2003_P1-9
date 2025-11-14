-- ============================================================
-- INF2003 Movie Database - Schema Creation Script
-- MariaDB Schema for Relational Data
-- ============================================================

-- Drop existing database if it exists
DROP DATABASE IF EXISTS movies_db;

-- Create new database
CREATE DATABASE movies_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE movies_db;

-- ============================================================
-- Table: USERS
-- Stores user information (for ratings)
-- ============================================================
CREATE TABLE USERS (
    userId INT PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB;

-- ============================================================
-- Table: MOVIES
-- Stores core movie information from MovieLens dataset
-- ============================================================
CREATE TABLE MOVIES (
    movieId INT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    release_date DATE,
    INDEX idx_title (title),
    INDEX idx_release_date (release_date)
) ENGINE=InnoDB;

-- ============================================================
-- Table: RATINGS
-- Stores user ratings for movies
-- NOTE: userId can be NULL to preserve ratings after user deletion
-- This maintains accurate movie averages and vote counts
-- ============================================================
CREATE TABLE RATINGS (
    userId INT NULL,
    movieId INT NOT NULL,
    rating DECIMAL(2,1) NOT NULL,
    timestamp BIGINT NOT NULL,
    PRIMARY KEY (movieId, timestamp, userId),
    FOREIGN KEY (userId) REFERENCES USERS(userId) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE,
    FOREIGN KEY (movieId) REFERENCES MOVIES(movieId) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    INDEX idx_rating (rating),
    INDEX idx_timestamp (timestamp),
    INDEX idx_movieId_rating (movieId, rating),
    INDEX idx_userId (userId),
    CONSTRAINT chk_rating CHECK (rating >= 0.5 AND rating <= 5.0)
) ENGINE=InnoDB;

-- ============================================================
-- Table: LINKS
-- Bridge table linking movieId to external IDs (imdbId, tmdbId)
-- This is crucial for joining SQL data with NoSQL (MongoDB) data
-- ============================================================
CREATE TABLE LINKS (
    movieId INT PRIMARY KEY,
    imdbId VARCHAR(20) NOT NULL,
    tmdbId INT NOT NULL,
    FOREIGN KEY (movieId) REFERENCES MOVIES(movieId) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    UNIQUE INDEX idx_imdbId (imdbId),
    UNIQUE INDEX idx_tmdbId (tmdbId)
) ENGINE=InnoDB;

-- ============================================================
-- View: popular_movies
-- Pre-computed view of movies with high ratings
-- (ADVANCED FEATURE for extra credit!)
-- ============================================================
CREATE VIEW popular_movies AS
SELECT 
    m.movieId,
    m.title,
    m.release_date,
    COUNT(r.rating) as rating_count,
    AVG(r.rating) as avg_rating,
    MIN(r.rating) as min_rating,
    MAX(r.rating) as max_rating
FROM MOVIES m
LEFT JOIN RATINGS r ON m.movieId = r.movieId
GROUP BY m.movieId, m.title, m.release_date
HAVING rating_count >= 10
ORDER BY avg_rating DESC;

-- ============================================================
-- Staging Tables (for data import and cleaning)
-- These allow you to import raw CSV data before validation
-- ============================================================

CREATE TABLE ratings_staging (
    userId INT,
    movieId INT,
    rating DECIMAL(2,1),
    timestamp BIGINT
) ENGINE=InnoDB;

CREATE TABLE links_staging (
    movieId INT,
    imdbId VARCHAR(20),
    tmdbId INT
) ENGINE=InnoDB;

-- ============================================================
-- Stored Procedure: Clean and Load Data from Staging
-- (ADVANCED FEATURE for extra credit!)
-- ============================================================
DELIMITER //

CREATE PROCEDURE load_from_staging()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Error loading data from staging tables';
    END;
    
    START TRANSACTION;
    
    -- Load unique users from ratings_staging
    INSERT IGNORE INTO USERS (userId)
    SELECT DISTINCT userId FROM ratings_staging;
    
    -- Load movies from links_staging (has movieId)
    INSERT IGNORE INTO MOVIES (movieId, title)
    SELECT DISTINCT movieId, CONCAT('Movie_', movieId)
    FROM links_staging;
    
    -- Load links
    INSERT IGNORE INTO LINKS (movieId, imdbId, tmdbId)
    SELECT movieId, imdbId, tmdbId
    FROM links_staging;
    
    -- Load ratings (only valid ones)
    INSERT IGNORE INTO RATINGS (userId, movieId, rating, timestamp)
    SELECT userId, movieId, rating, timestamp
    FROM ratings_staging
    WHERE rating BETWEEN 0.5 AND 5.0;
    
    COMMIT;
END //

DELIMITER ;

-- ============================================================
-- Display table information
-- ============================================================
SHOW TABLES;

SELECT 
    TABLE_NAME,
    TABLE_TYPE,
    ENGINE,
    TABLE_ROWS,
    AVG_ROW_LENGTH,
    DATA_LENGTH
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'movies_db'
ORDER BY TABLE_NAME;
