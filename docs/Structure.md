**Root Directory:**

- `.babelrc`: Configuration file for Babel, a JavaScript compiler. It specifies the presets used to transform JSX syntax into standard JavaScript that browsers can understand. In this case, it uses the `@babel/preset-react` preset for React.
- `.gitignore`: Specifies intentionally untracked files that Git should ignore. This includes virtual environment directories, build artifacts, database files, and other sensitive or auto-generated files.
- `build.js`: A Node.js script that automates the process of building the JavaScript files. It compiles JSX files using Babel and copies other static assets from the source directory (`website/static/js`) to the destination directory (`staticfiles/js`).
- `CONTRIBUTING.md`: A Markdown file that provides guidelines for contributing to the project, including setup instructions, coding standards, and the contribution workflow.
- `LICENSE`: Contains the license information for the project.
- `Makefile`: A file containing a set of commands to automate common development tasks, such as running the server, cleaning sessions, collecting static files, and running database migrations.
- `manage.py`: A command-line utility for Django that provides various commands for managing the project, such as running the development server, creating database migrations, and running tests.
- `package.json`: A Node.js package manifest file that contains metadata about the project, including dependencies and scripts.
- `requirements.txt`: A text file that lists the Python packages required to run the project. This file is used by `pip` to install the project's dependencies.

- `website/`: This directory contains the core Django project files.

  - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
  - `asgi.py`: Configuration for ASGI (Asynchronous Server Gateway Interface), used for deploying Django with asynchronous capabilities.
  - `celery.py`: Configuration file for Celery, a distributed task queue. It defines the Celery app and configures it to use Redis as the broker and Django's database as the result backend. It also defines beat schedules for periodic tasks.
  - `settings.py`: Contains all the Django project settings, such as database configuration, installed apps, middleware, template settings, static files configuration, and security settings.
  - `urls.py`: Defines the URL patterns for the entire project, mapping URLs to specific views.
  - `wsgi.py`: Configuration for WSGI (Web Server Gateway Interface), used for deploying Django with traditional web servers.

  **root_assets:**

  - `browserconfig.xml`: Configuration file for Microsoft browsers, defining tile images for pinned sites.
  - `crossdomain.xml`: Policy file for Adobe Flash Player, controlling access to data across domains.
  - `favicon.ico`: The favicon for the website, displayed in the browser tab.
  - `humans.txt`: A text file containing information about the people who built the website.
  - `robots.txt`: A text file that provides instructions to web robots (crawlers) about which parts of the website should not be indexed.
  - `tile-wide.png`: A wide tile image for pinned sites in Microsoft browsers.
  - `tile.png`: A square tile image for pinned sites in Microsoft browsers.

  **static:**

  - `css/`: Contains CSS stylesheets for the website.

    - `web/`: Contains CSS stylesheets specific to the web app.

      - `auth.css`: CSS stylesheet for authentication-related pages (login, signup).
      - `base.css`: CSS stylesheet for the base template, defining the overall layout and styling of the website.
      - `course_detail.css`: CSS stylesheet for the course detail page.
      - `course_review_search.css`: CSS stylesheet for the course review search page.
      - `current_term.css`: CSS stylesheet for the current term page.
      - `landing.css`: CSS stylesheet for the landing page.

    - `fonts/`: Contains font files used by the website.

      - `glyphicons-halflings-regular.eot`: Embedded OpenType font file for Glyphicons Halflings.
      - `glyphicons-halflings-regular.ttf`: TrueType font file for Glyphicons Halflings.
      - `glyphicons-halflings-regular.woff`: Web Open Font Format file for Glyphicons Halflings.
      - `glyphicons-halflings-regular.woff2`: Web Open Font Format 2.0 file for Glyphicons Halflings.
      - `glyphicons-halflings-regular.svg`: SVG font file for Glyphicons Halflings.

  - `img/`: Contains image files used by the website.

    - `logo-sm.png`: A small logo image.
    - `logo.svg`: An SVG version of the logo.

  - `js/`: Contains JavaScript files for the website.

    - `plugins.js`: Contains JavaScript plugins and helper functions.
    - `vendor/`: Contains third-party JavaScript libraries.

      - `jquery.highlight-5.js`: A jQuery plugin for highlighting text.

    - `web/`: Contains JavaScript files specific to the web app.

      - `base.jsx`: Base JavaScript file for setting up AJAX requests with CSRF protection.
      - `common.jsx`: Contains common JavaScript functions used throughout the website.
      - `course_detail.jsx`: JavaScript file for the course detail page, handling professor autocompletion and median chart rendering.
      - `course_review_search.jsx`: JavaScript file for the course review search page, handling text highlighting.
      - `current_term.jsx`: JavaScript file for the current term page, handling upvoting and downvoting courses.
      - `landing.jsx`: JavaScript file for the landing page, handling focus on the search input.

- `apps/`: This directory contains the Django apps that make up the project.

  - `analytics/`: This app handles analytics-related functionality.

    - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
    - `apps.py`: Configuration file for the analytics app.
    - `forms.py`: Defines the `ManualSentimentForm`, which is used to manually label the sentiment of reviews.
    - `migrations/`: Contains database migration files for the analytics app.
    - `models.py`: Contains models specific to the analytics app.
    - `tasks.py`: Defines Celery tasks for the analytics app, such as sending analytics email updates and possibly requesting a term update.
    - `views.py`: Defines the views for the analytics app, such as the analytics dashboard and the sentiment labeler.
    - `templates/analytics/`: Contains HTML templates for the analytics app.

      - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
      - `0001_initial.py`: The initial migration file for the `spider` app, defining the `CrawledData` model and its fields.

      - `analytics_email.txt`: A text template used to generate the content of the weekly analytics email.
      - `dashboard.html`: HTML template for the analytics dashboard, displaying various statistics and links to admin pages.
      - `eligible_for_recommendations.html`: HTML template for displaying users eligible for recommendations based on their voting activity.
      - `sentiment_labeler.html`: HTML template for the sentiment labeler tool, used to manually label the sentiment of reviews.

  - `recommendations/`: This app handles course recommendation functionality.

    - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
    - `admin.py`: Registers the `Recommendation` model with the Django admin interface.
    - `apps.py`: Configuration file for the recommendations app.
    - `migrations/`: Contains database migration files for the recommendations app.
      - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
      - `0001_initial.py`: The initial migration file for the `recommendations` app, defining the `Recommendation` model and its fields.
    - `models.py`: Defines the `Recommendation` model, which represents a course recommendation for a user.
    - `tasks.py`: Defines Celery tasks for the recommendations app, such as generating course description similarity recommendations.
    - `templates/recommendations/`: Contains HTML templates for the recommendations app.
      - `recommendations.html`: HTML template for displaying course recommendations to users.
    - `views.py`: Defines the views for the recommendations app, such as the recommendations list.

  - `spider/`: This app handles web scraping and data crawling functionality.

    - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
    - `apps.py`: Configuration file for the spider app.
    - `crawlers/`: Contains the web scraping logic for different data sources.
      - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
      - `medians.py`: Contains the web scraping logic for retrieving course median data from the Registrar's website.
      - `orc.py`: Contains the web scraping logic for retrieving course information from the Organization, Regulations, and Courses (ORC) website.
      - `timetable.py`: Contains the web scraping logic for retrieving course timetable data from the Academic Timetable website.
    - `migrations/`: Contains database migration files for the spider app.

      - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
      - `0001_initial.py`: The initial migration file for the `spider` app, defining the `CrawledData` model and its fields.
      - `0002_alter_crawleddata_current_data_and_more.py`: Migration file to update the `CrawledData` model, setting `null=True` and `blank=True` for `current_data` and setting default values for `data_type` and `resource`.

    - `models.py`: Defines the `CrawledData` model, which stores crawled data from various sources.
    - `tasks.py`: Defines Celery tasks for the spider app, such as crawling the ORC, timetable, and medians.
    - `templates/spider/`: Contains HTML templates for the spider app.
      - `crawled_data_detail.html`: HTML template for displaying the details of a specific `CrawledData` object.
      - `crawled_data_list.html`: HTML template for displaying a list of `CrawledData` objects.
    - `utils.py`: Contains utility functions for the spider app, such as retrieving and parsing HTML content.
    - `views.py`: Defines the views for the spider app, such as the crawled data list and detail views.

  - `web/`: This app handles the core website functionality, such as course reviews, user authentication, and search.

    - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
    - `admin.py`: Registers the models with the Django admin interface.
    - `apps.py`: Configuration file for the web app.
    - `migrations/`: Contains database migration files for the web app.
    - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
      - `0001_initial.py`: The initial migration file for the `web` app, defining the initial set of models and their fields.
      - `0002_alter_student_unauth_session_ids.py`: Migration file to alter the `unauth_session_ids` field in the `Student` model, using `django.contrib.postgres.fields.ArrayField`.
      - `0003_alter_course_unique_together_course_course_code_and_more.py`: Migration file to change the `Course` model, including removing unique together constraint, adding `course_code`, `course_credits`, `course_title`, `course_topics`, `pre_requisites`, altering `description`, adding unique constraint for `course_code`, and removing `department`, `number`, `source`, `subnumber`, and `title` fields.
      - `0004_course_department.py`: Migration file to add the `department` field to the `Course` model.
      - `0005_course_number_alter_course_course_code.py`: Migration file to add the `number` field to the `Course` model and alter the `course_code` field.
    - `models/`: Contains the data models for the web app.

      - `__init__.py`: Imports all models, making them available for use in other parts of the app.
      - `course.py`: Defines the `Course` model, which represents a course offering.
      - `course_offering.py`: Defines the `CourseOffering` model, which represents a specific instance of a course being offered in a particular term.
      - `distributive_requirement.py`: Defines the `DistributiveRequirement` model, which represents a distributive requirement that a course may fulfill.
      - `instructor.py`: Defines the `Instructor` model, which represents an instructor who teaches a course.
      - `course_median.py`: Defines the `CourseMedian` model, which stores grade medians for a course offering.
      - `review.py`: Defines the `Review` model, which represents a student review of a course.
      - `vote.py`: Defines the `Vote` model, which represents a user's vote on a course's quality or difficulty.
      - `student.py`: Defines the `Student` model, which extends the Django `User` model with additional information about students.
      - `forms/`: Contains Django forms for the web app.

        - `__init__.py`: Imports all forms, making them available for use in other parts of the app.
        - `review_form.py`: Defines the `ReviewForm`, which is used to create and edit course reviews.
        - `signup_form.py`: Defines the `SignupForm`, which is used to register new users.

    - `templates/web/`: Contains HTML templates for the web app.

      - `base.html`: The base template for all HTML pages, defining the basic structure and layout of the website.
      - `components/`: Contains reusable HTML snippets.

        - `course_summary.html`: HTML template for displaying a summary of a course.

      - `confirmation.html`: HTML template for displaying the account confirmation page.
      - `course_detail.html`: HTML template for displaying the details of a specific course.
      - `course_review_search.html`: HTML template for displaying the results of a course review search.
      - `course_search.html`: HTML template for displaying the results of a course search.
      - `current_term.html`: HTML template for displaying the courses offered in the current term.
      - `departments.html`: HTML template for displaying a list of departments.
      - `footer.html`: HTML template for the website footer.
      - `instructions.html`: HTML template for displaying instructions after successful registration.
      - `landing.html`: HTML template for the landing page.
      - `login.html`: HTML template for the login page.
      - `logout.html`: HTML template for the logout page.
      - `navbar.html`: HTML template for the website navigation bar.
      - `password_reset_complete.html`: HTML template for displaying the password reset complete page.
      - `password_reset_confirm.html`: HTML template for displaying the password reset confirmation form.
      - `password_reset_done.html`: HTML template for displaying the password reset done page.
      - `password_reset_email.html`: HTML template for the password reset email.
      - `password_reset_form.html`: HTML template for the password reset form.
      - `signup.html`: HTML template for the signup page.

    - `tests/`: Contains unit tests for the web app.

      - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
      - `factories.py`: Defines Factory Boy factories for creating test data.
      - `lib_tests/`: Contains unit tests for the `lib` directory.

        - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
        - `test_grades.py`: Defines unit tests for the `lib/grades.py` module.
        - `test_terms.py`: Defines unit tests for the `lib/terms.py` module.

      - `model_tests/`: Contains unit tests for the models.

        - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
        - `test_course.py`: Defines unit tests for the `Course` model.
        - `test_student.py`: Defines unit tests for the `Student` model.
        - `test_vote.py`: Defines unit tests for the `Vote` model.

    - `views.py`: Defines the views for the web app, such as the landing page, course detail page, and search results page.

- `scripts/`: Contains helper scripts for development and deployment.

  - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
  - `crawl_and_import_data.py`: A script to crawl and import data.

- `lib/`: Contains reusable Python modules.

  - `__init__.py`: An empty file that tells Python that this directory should be considered a Python package.
  - `constants.py`: Defines constant values used throughout the project, such as the current term and support email address.
  - `departments.py`: Provides a mapping of department codes to department names.
  - `grades.py`: Provides functions for converting letter grades to numeric values.
  - `task_utils.py`: Contains utility functions for Celery tasks, such as sending error emails.
  - `terms.py`: Provides functions for working with academic terms, such as validating term formats and calculating term values.
