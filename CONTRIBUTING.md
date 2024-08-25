# Development

Environment: Linux, python3.12

1. `git clone git@github.com:TechJI-2023/CourseReview.git`
2. `cd CourseReview`
3. `git checkout py3`
4. `python3 -m venv .venv`
5. `python3 -m pip install -r requirements.txt`
6. Make directory for builds of static files: `mkdir staticfiles`
7. Create .env file for storing secrets:
   ```bash
   cat <<EOF > .env
   DATABASE_URL=postgres://admin:test@localhost:5432/coursereview
   REDIS_URL=redis://[YOUR_USERNAME]@localhost:6379
   SECRET_KEY=02247f40-a769-4c49-9178-4c038048e7ad
   DEBUG=True
   CURRENT_TERM=2024
   OFFERINGS_THRESHOLD_FOR_TERM_UPDATE=100
   EOF
   ```
8. Build static files: `echo 'yes' | make collect`
9. Configure database
   1. Install Postgres: `sudo pacman -S postgresql`
   2. Create user postgres: `sudo -iu postgres`
   3. Initialize database: `initdb -D /var/lib/postgres/data`
   4. Start postgresql service: `sudo systemctl start postgresql`. Run `sudo systemctl enable postgresql` to auto-start postgresql service.
   5. Switch to user postgres: `sudo -iu postgres`
   6. `psql`
   7. Initialize coursereview database, user and privileges
      ```sql
      CREATE DATABASE coursereview;
      CREATE USER admin WITH PASSWORD 'test';
      GRANT ALL PRIVILEGES ON DATABASE coursereview TO admin;
      ALTER DATABASE coursereview OWNER TO admin;
      ```
   8. Exit psql and switch back to normal user: `\q`, `exit`
   9. Configure postgres to listen on all interfaces (DO NOT do this in production): `sudo vim /var/lib/postgres/data/postgresql.conf`,
      ```conf
      listen_addresses = '0.0.0.0'
      ```
   10. Grant permission to connect to postgres from any ip (DO NOT do this in production): `sudo vim /var/lib/postgres/data/pg_hba.conf` and add a line:
       ```conf
       host    all             all             0.0.0.0/0            md5
       ```
   11. Restart postgres service: `sudo systemctl restart postgresql`
   12. Auto setup database connection and static file routes in Django: `make migrate`
10. `make run` and visit http://127.0.0.1:8000
