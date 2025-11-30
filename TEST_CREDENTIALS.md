# Test Credentials

## User Accounts

| Role  | Username | Password    |
|-------|----------|-------------|
| User  | testuser | password123 |
| Admin | admin    | password123 |

## Web Deployment (Live Demo)

### Access URLs
| Session | URL | Purpose |
|---------|-----|---------|
| User A | http://34.87.19.224:6080/vnc.html | Primary session |
| User B | http://34.87.19.224:6081/vnc.html | Concurrency testing |

### Testing Transaction Locks
1. Open both URLs in separate browser windows
2. Login as different users (e.g. admin + testuser)
3. Both go to "Users & Ratings" tab
4. Both try to edit the same movie rating
5. Second user should see "Currently editing by [user]..." message

## Database Connections

### MariaDB
- **Host:** localhost (or `mariadb` in Docker)
- **Port:** 3306
- **Database:** movies_db
- **User:** root
- **Password:** 12345 *(use your own SQL password for local setup)*

### MongoDB Atlas
```
mongodb+srv://nkt12385_db_user:Keetian12345@cluster0.qrc4kkf.mongodb.net/
```
- **Database:** movies_nosql
- **Collection:** tmdb_movies
