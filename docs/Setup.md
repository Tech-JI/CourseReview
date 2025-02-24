# Development

Environment:

- Ubuntu Linux (most modern Linux distros and MacOS are supposedly supported. Use your corresponding package manager. This guide uses ubuntu/debian's `apt` and python `pip`.)

- python 3.10 to 3.13

---

1. `git clone git@github.com:TechJI-2023/CourseReview.git`

2. `cd CourseReview`

3. `git checkout dev`

4. `python3 -m venv .venv`

5. `source .venv/bin/activate`

6. `python3 -m pip install -r requirements.txt`

7. Make directory for builds of static files: `mkdir staticfiles`

8. Create .env file for storing secrets. The contents should be like:

   ```ini
   # PostgreSQL
   DB_USER=admin
   DB_PASSWORD=test
   DB_HOST=127.0.0.1
   DB_PORT=5432
   REDIS_URL=redis://localhost:6379/0
   SECRET_KEY=02247f40-a769-4c49-9178-4c038048e7ad
   DEBUG=True
   OFFERINGS_THRESHOLD_FOR_TERM_UPDATE=100
   ```

9. Build static files: `echo 'yes' | make collect`

10. Configure database

    1. Install Postgres: 
      - `sudo apt update`
      - `sudo apt install postgresql`

    2. Create user postgres: `sudo -iu postgres`

    3. Initialize database: `initdb -D /var/lib/postgres/data`

    4. Start postgresql service: `sudo systemctl start postgresql`. Run `sudo systemctl enable postgresql` to auto-start postgresql service on start-up.

    5. Switch to user postgres: `sudo -iu postgres`

    6. `psql`

    7. Initialize coursereview database, user and privileges

       ```sql
       CREATE DATABASE coursereview;
       CREATE USER admin WITH PASSWORD 'test'; -- This is the same password of admin in .env file above.
       GRANT ALL PRIVILEGES ON DATABASE coursereview TO admin;
       ALTER DATABASE coursereview OWNER TO admin;
       ```

      get the path of config file: 
      ```
      SHOW config_file;
      ```
      copy the path, Shift+Ctrl+C (default)

    8. Exit psql and switch back to normal user: `\q`, `exit`

    9.  Configure postgres to listen on all interfaces (DO NOT do this in production): `sudo vim {Path to your config file}`, example: `sudo vim /etc/postgresql/14/main/postgresql.conf`. Find the line `listen_addresses`, modify it to: 

       ```ini
       listen_addresses = '0.0.0.0'
       ```

    10. Grant permission to connect to postgres from any IP (DO NOT do this in production): `sudo vim /etc/postgresql/14/main/pg_hba.conf` (maybe differ from your path, just change the command according to the copied path) and add a line:

        ```ini
        host    all             all             0.0.0.0/0            md5
        ```

    11. Restart postgres service: `sudo systemctl restart postgresql`

    12. Auto setup database connection and static file routes in Django: `make migrate`, `make makemigrations`

11. Install cache database redis: `sudo apt install redis-server`, `sudo systemctl start redis`. Run `sudo systemctl enable redis` to auto-start redis service on start-up.

12. `make run` and visit http://127.0.0.1:8000

13. Add local admin:

    1. `python manage.py createsuperuser`. The email can be blank. Use a strong password in production.

    2. Enter interactive python shell: `make shell`. (Different from directly running `python` from shell.)

    3. Run following python codes in interactive shell:
       ```python
       from django.contrib.auth.models import User
       u = User.objects.last()
       u.is_active = True
       u.is_staff = True
       u.is_admin = True
       u.save()
       ```

14. Crawl data from JI official website:

    1. Edit `COURSE_DETAIL_URL_PREFIX` in `apps/spider/crawlers/orc.py`: Add a number after url param `id` like this: `...?id=23`, so only course id starting from 23 (e.g. 230-239, 2300) will be crawled, so as to save time during development. Remember not to commit this change.

    2. Enter interactive python shell: `make shell`.

    3. Run following python codes in interactive shell:
       ```python
       from scripts import crawl_and_import_data
       crawl_and_import_data()
       ```
