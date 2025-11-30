# Test Credentials

## User Accounts

| Role  | Username | Password    |
|-------|----------|-------------|
| User  | testuser | password123 |
| Admin | admin    | password123 |

## Web Deployment (Live Demo)

### Access URLs
| Session | URL | Purpose |
|---------|-----|--------|
| User A | http://34.87.19.224:6080/vnc.html | Primary session |
| User B | http://34.87.19.224:6081/vnc.html | Concurrency testing |
| User C | http://34.87.19.224:6082/vnc.html | Concurrency testing |
| User D | http://34.87.19.224:6083/vnc.html | Concurrency testing |
| User E | http://34.87.19.224:6084/vnc.html | Concurrency testing |

### Testing Transaction Locks
1. Open multiple URLs (2-5) in separate browser windows
2. Login as different users (admin, testuser, or create new accounts)
3. All users go to "Users & Ratings" tab
4. All try to edit the same movie rating simultaneously
5. Only the first user to lock can edit
6. Other users see "Currently editing by [user]..." message
7. When first user saves/cancels, next user can lock and edit

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
