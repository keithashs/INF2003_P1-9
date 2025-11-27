# TMDB Movie Database
## Hybrid SQL-NoSQL Movie Database System

---

## Project Overview
A hybrid database system integrating MariaDB (SQL) and MongoDB (NoSQL) for movie data management, demonstrating polyglot persistence principles.

---

## Quick Start

### Prerequisites
- Python 3.8+
- MariaDB 10.x / MySQL 5.7+
- MongoDB Atlas account

### Installation

**1. Install Dependencies**
```bash
python setup.py
```

**2. Configure Database (Optional)**
```bash
# Windows PowerShell
$env:DB_PASS="your_mariadb_password"
$env:MONGO_USERNAME="your_mongo_username"
$env:MONGO_PASSWORD="your_mongo_password"
$env:MONGO_CLUSTER="your_cluster.mongodb.net"
```

**3. Set Up Database**
```bash
mysql -u root -p < 1_create_schema.sql
python 2_import_data.py
mysql -u root -p movies_db < 3_create_indexes.sql
# Run remaining SQL scripts (4-8) in order
```

**4. Run Application**
```bash
python gui.py
```

---

## System Architecture

### Why Two Databases? (Polyglot Persistence)

**MariaDB (SQL)** - For structured, relational data:
- Stores: Users, Movies, Ratings, Links
- Enforces referential integrity with foreign keys
- Handles transactional operations (ACID)
- Efficient for joins and aggregations (COUNT, AVG, GROUP BY)

**MongoDB (NoSQL)** - For flexible metadata:
- Stores: Rich movie details (genres, keywords, overview, revenue)
- Schema-less design handles variable fields
- Fast regex searches on text
- No junction tables needed for arrays

**Integration**: Python GUI joins both using `tmdbId` as bridge field.

---

## Database Schemas

### MariaDB Tables

```sql
-- Users
USERS (userId, username, email)

-- Movies
MOVIES (movieId, title, release_date)

-- Ratings (composite PK)
RATINGS (userId, movieId, rating, timestamp)
  - rating CHECK (0.5 to 5.0)
  - Foreign keys with CASCADE

-- Links (bridge to MongoDB)
LINKS (movieId, imdbId, tmdbId)
```

### MongoDB Collection

```json
tmdb_movies {
  "tmdbId": 603,
  "title": "The Matrix",
  "genres": "Action, Science Fiction",
  "keywords": "virtual reality, AI",
  "overview": "...",
  "vote_average": 8.4,
  "revenue": 825532764
}
```

**Indexes**: tmdbId, genres, keywords

---

## Key Features

### SQL Operations
- Full CRUD (Create, Read, Update, Delete)
- Aggregations (AVG, COUNT, MIN, MAX)
- Nested subqueries and multi-table joins
- Dynamic filtering

### NoSQL Operations
- Genre/keyword regex search
- Aggregation pipelines
- Content-based recommendations
- Flexible schema queries

### GUI Features
- Movie search (hybrid SQL + NoSQL results)
- User & rating management
- Performance comparison metrics
- Concurrent edit protection

---

## Design Highlights

### Why This Architecture?

1. **SQL Strengths**: Relationships, transactions, integrity
2. **NoSQL Strengths**: Flexibility, text search, scaling
3. **Together**: Best of both worlds - use the right tool for each job

### Data Flow
1. User searches → GUI
2. SQL query → gets ratings, movieId
3. MongoDB query → gets metadata via tmdbId
4. GUI displays combined results

---

## References

[1] Kaggle, "TMDb Movies Dataset 2023"  
[2] R. Banik, "The Movies Dataset," 2017  
[3] M. Fowler, *NoSQL Distilled: Polyglot Persistence*, 2012
