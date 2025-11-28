// ============================================================
// MongoDB Initialization Script
// ============================================================
// Creates the database, collection, and application user
// Runs automatically on first container startup
// ============================================================

// Switch to the movies database
db = db.getSiblingDB('movies_nosql');

// Create application user with read/write access
db.createUser({
    user: 'movies_user',
    pwd: 'movies_pass',
    roles: [
        { role: 'readWrite', db: 'movies_nosql' }
    ]
});

// Create the tmdb_movies collection with validation
db.createCollection('tmdb_movies', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['id', 'title'],
            properties: {
                id: {
                    bsonType: 'int',
                    description: 'TMDB movie ID - required'
                },
                title: {
                    bsonType: 'string',
                    description: 'Movie title - required'
                },
                overview: {
                    bsonType: 'string',
                    description: 'Movie overview/synopsis'
                },
                genres: {
                    bsonType: 'string',
                    description: 'Comma-separated genre list'
                },
                keywords: {
                    bsonType: 'string',
                    description: 'Comma-separated keywords'
                },
                vote_average: {
                    bsonType: 'double',
                    description: 'Average vote rating'
                },
                vote_count: {
                    bsonType: 'int',
                    description: 'Number of votes'
                },
                revenue: {
                    bsonType: 'long',
                    description: 'Movie revenue'
                },
                runtime: {
                    bsonType: 'int',
                    description: 'Runtime in minutes'
                },
                original_language: {
                    bsonType: 'string',
                    description: 'Original language code'
                },
                release_date: {
                    bsonType: 'string',
                    description: 'Release date string'
                },
                tagline: {
                    bsonType: 'string',
                    description: 'Movie tagline'
                },
                popularity: {
                    bsonType: 'double',
                    description: 'Popularity score'
                }
            }
        }
    },
    validationLevel: 'moderate',
    validationAction: 'warn'
});

// Create indexes for common queries
db.tmdb_movies.createIndex({ 'id': 1 }, { unique: true, name: 'idx_tmdb_id' });
db.tmdb_movies.createIndex({ 'title': 'text', 'overview': 'text', 'keywords': 'text' }, { name: 'idx_text_search' });
db.tmdb_movies.createIndex({ 'genres': 1 }, { name: 'idx_genres' });
db.tmdb_movies.createIndex({ 'vote_average': -1 }, { name: 'idx_vote_avg' });
db.tmdb_movies.createIndex({ 'popularity': -1 }, { name: 'idx_popularity' });

print('✅ MongoDB initialization complete!');
print('   - Database: movies_nosql');
print('   - Collection: tmdb_movies');
print('   - User: movies_user created');
print('   - Indexes: created for optimized queries');
