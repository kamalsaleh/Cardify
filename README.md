# Cardify App

Cardify is a Flask-based web application designed to assit you create, manage, and utilize flashcards for learning, memorization, planning tasks, etc.

## Features
- Create flashcards with custom fields: title, content, hint, notes and image.
- Generate cards using the open-ai model "gpt-4o".
- Generate images for the cards using the open-ai model "dall-e-3".
- Create topics (topics can be parents of other topics)
- For each topic create one or more decks and add flashcards to decks.
- Visualize topics, decks and flashcards in a graphical way using the "pyvis" package.

## Run the website on a local machine
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <repository_folder>
   ```

2. Install the required dependencies (pereferibly in a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```

3. Set up a new MySQL database:
    - Access MySQL command line:
    ```bash
    sudo su
    mysql -u root -p
    ```
    - Create a new database:
    ```sql
    CREATE DATABASE your_database_name;
    ```
    - Create a new user and grant privileges:
    ```sql
    CREATE USER 'your_mysql_user'@'localhost' IDENTIFIED BY 'your_mysql_password';
    GRANT ALL PRIVILEGES ON your_database_name.* TO 'your_mysql_user'@'localhost';
    FLUSH PRIVILEGES;
    ```
    - Verify the new database has been created:
    ```sql
    SHOW DATABASES;
    ```
    - Exit MySQL command line:
    ```sql
    exit;
    ```
    - You can access your database using
    ```bash
    mysql -u your_mysql_user -p
    ```

4. Copy/Rename the file `keys.py.tmp` to `keys.py` and add the following content:
  ```python
  MYSQL_USER = 'your_mysql_user'
  MYSQL_PASSWORD = 'your_mysql_password'
  MYSQL_HOST = 'localhost' # adjust if needed
  DATABASE_NAME = 'your_database_name'
  ```

5. If you have an OpenAI key, add it to the `keys.py` file:
  ```python
  OPENAI_API_KEY = 'your_openai_api_key'
  ```

6. Run the application:
   ```bash
   flask run
   ```

7. Open the application in your browser at `http://127.0.0.1:5000`.