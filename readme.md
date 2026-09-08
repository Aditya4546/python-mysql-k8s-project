---
docker pull mysql:8.0
---

docker run -d ^
  --name task-mysql ^
  -e MYSQL_ROOT_PASSWORD=root123 ^
  -e MYSQL_DATABASE=taskdb ^
  -e MYSQL_USER=appuser ^
  -e MYSQL_PASSWORD=app123 ^
  -p 3306:3306 ^
  mysql:8.0

---

docker ps

---

docker logs task-mysql

Wait until you see something similar to:

"ready for connections"
---


Create init.sql:


USE taskdb;

CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

---
Now copy it into the MySQL container.

docker cp init.sql task-mysql:/init.sql

---


Execute it:
docker exec -i task-mysql mysql -uappuser -papp123 taskdb < init.sql

note: will show warning dont mind it
---

Verify:

docker exec -it task-mysql mysql -uappuser -papp123 taskdb

inside mysql : 
  SHOW TABLES;

  DESCRIBE tasks;

  exit;

---
Create a virtual environment:

python -m venv venv

Activate it on Windows:

venv\Scripts\activate

---

Create:

requirements.txt


Flask==3.1.2
mysql-connector-python==9.4.0
python-dotenv==1.1.1

---

Install:

pip install -r requirements.txt

---

Create:
.env


DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=appuser
DB_PASSWORD=app123
DB_NAME=taskdb

---

Create:

database.py

"""
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

"""
This file has one responsibility:

Create a connection between Python and MySQL
---


Create Flask application

Create:

app.py

"""
from flask import Flask, request, jsonify
from database import get_connection

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "message": "Task Management API is running"
    })


@app.route("/health")
def health():
    try:
        connection = get_connection()

        if connection.is_connected():
            connection.close()

            return jsonify({
                "status": "healthy",
                "database": "connected"
            })

    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 500


@app.route("/tasks", methods=["GET"])
def get_tasks():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, description, completed, created_at
        FROM tasks
        ORDER BY id DESC
    """)

    tasks = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(tasks)


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, title, description, completed, created_at
        FROM tasks
        WHERE id = %s
        """,
        (task_id,)
    )

    task = cursor.fetchone()

    cursor.close()
    connection.close()

    if task is None:
        return jsonify({
            "error": "Task not found"
        }), 404

    return jsonify(task)


@app.route("/tasks", methods=["POST"])
def create_task():

    data = request.get_json()

    if not data or "title" not in data:
        return jsonify({
            "error": "Title is required"
        }), 400

    title = data["title"]
    description = data.get("description", "")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO tasks (title, description)
        VALUES (%s, %s)
        """,
        (title, description)
    )

    connection.commit()

    task_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return jsonify({
        "message": "Task created",
        "task_id": task_id
    }), 201


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):

    data = request.get_json()

    title = data.get("title")
    description = data.get("description")
    completed = data.get("completed")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET title = %s,
            description = %s,
            completed = %s
        WHERE id = %s
        """,
        (title, description, completed, task_id)
    )

    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        connection.close()

        return jsonify({
            "error": "Task not found"
        }), 404

    cursor.close()
    connection.close()

    return jsonify({
        "message": "Task updated"
    })


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id = %s",
        (task_id,)
    )

    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        connection.close()

        return jsonify({
            "error": "Task not found"
        }), 404

    cursor.close()
    connection.close()

    return jsonify({
        "message": "Task deleted"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

"""

Run the application app.py

* Running on http://127.0.0.1:5000
---

Test the database connection

http://localhost:5000/health

---

Create:

.gitignore and add below files init

venv/
__pycache__/
*.pyc
.env


---


☐ Docker is running

☐ MySQL container is running

☐ taskdb exists

☐ tasks table exists

☐ Python virtual environment works

☐ Flask starts

☐ / endpoint works

☐ /health says database = connected

☐ POST /tasks works

☐ GET /tasks works

☐ GET /tasks/<id> works

☐ PUT /tasks/<id> works

☐ DELETE /tasks/<id> works

☐ Data is visible inside MySQL

☐ .env is excluded from Git

---


stage 2 : 2: Dockerize the Python application

We are going to recreate it properly with a Docker network and persistent storage.


stop the docker mysql container: 

docker stop task-mysql

Remove it:

docker rm task-mysql

Don't worry about the database for now. We're going to create a proper Docker volume so that our database survives container recreation.

Create a Docker network

docker network create task-network

Verify:

docker network ls

Our architecture will now be:

task-network
       │
       ├───────────────┐
       │               │
       ▼               ▼
Python Container   MySQL Container

---

Create a MySQL volume

docker volume create task-mysql-data

---
Check:
docker volume ls


The architecture becomes:

MySQL Container
      │
      ▼
task-mysql-data
      │
      ▼
Persistent Database

-------
Start MySQL again

docker run -d ^
  --name task-mysql ^
  --network task-network ^
  -e MYSQL_ROOT_PASSWORD=root123 ^
  -e MYSQL_DATABASE=taskdb ^
  -e MYSQL_USER=appuser ^
  -e MYSQL_PASSWORD=app123 ^
  -v task-mysql-data:/var/lib/mysql ^
  mysql:8.0



----
Check:

docker ps

---

Recreate the tasks table

Because this is a new volume, execute your existing init.sql

Make sure init.sql still contains:

"""

USE taskdb;

CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

"""
---

Then:

docker exec -i task-mysql mysql -uappuser -papp123 taskdb < init.sql

---

verify:

docker exec -it task-mysql mysql -uappuser -papp123 taskdb

SHOW TABLES;

exit;


---

Create the Dockerfile

"""
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY database.py .

EXPOSE 5000

CMD ["python", "app.py"]
"""

From your project directory:

docker build -t task-python-app .

---

Verify:

docker images

You should see:

task-python-app

---

Run the Python container

Now comes the important part.

Run:

docker run -d ^
  --name task-python ^
  --network task-network ^
  -p 5000:5000 ^
  -e DB_HOST=task-mysql ^
  -e DB_PORT=3306 ^
  -e DB_USER=appuser ^
  -e DB_PASSWORD=app123 ^
  -e DB_NAME=taskdb ^
  task-python-app

---

Understand DB_HOST=task-mysql

This is probably the most important command in this entire lab:

-e DB_HOST=task-mysql

Why?

Because both containers are connected to:

task-network

Docker provides internal DNS.

So:

task-mysql

resolves to the MySQL container.

Therefore:

Python
   │
   │ task-mysql:3306
   ▼
MySQL

We don't need to know the MySQL container's IP address.

And we don't use:

localhost


---

Check both containers

Run:

docker ps

You should see:

CONTAINER
────────────────
task-python
task-mysql

---
Now:

Docker
    │
task-network
    ├── task-python
    │      │
    │      └── Flask :5000
    │
    └── task-mysql
           │
           └── MySQL :3306

---

Check Python logs

Run:

docker logs task-python
docker logs task-python

You should see something like:

* Running on all addresses (0.0.0.0)
* Running on http://127.0.0.1:5000
* Running on http://172.x.x.x:5000
---

est from your browser

Open:

http://localhost:5000

Expected:

{
    "message": "Task Management API is running"
}

Remember:

Browser
   │
   │ localhost:5000
   ▼
Windows
   │
   │ port mapping
   ▼
Python Container

The -p option created this mapping:

5000 → 5000



---

Test the database connection

Open:

http://localhost:5000/health

----

Browser
   │
   │ localhost:5000
   ▼
┌─────────────────────┐
│  Python Container   │
│                     │
│  Flask              │
└──────────┬──────────┘
           │
           │ task-mysql:3306
           ▼
┌─────────────────────┐
│   MySQL Container   │
│                     │
│   taskdb            │
└──────────┬──────────┘
           │
           ▼
    Docker Volume


---


Create
POST http://localhost:5000/tasks
{
    "title": "Learn Kubernetes",
    "description": "Move this application to Kubernetes"
}
Read
GET http://localhost:5000/tasks
Single task
GET http://localhost:5000/tasks/1
Update
PUT http://localhost:5000/tasks/1   


{
    "title": "Learn Kubernetes",
    "description": "Learn Pods and Services",
    "completed": true
}
Delete
DELETE http://localhost:5000/tasks/1


----

Test Docker networking directly

docker network inspect task-network

---

Test database persistence

This is another important Docker concept.
---
stop the MySQL container:

docker stop task-mysql

---

Remove it:

docker rm task-mysql

---

Now recreate it using the same volume:

docker run -d --name task-mysql --network task-network -e MYSQL_ROOT_PASSWORD=root123 -e MYSQL_DATABASE=taskdb -e MYSQL_USER=appuser -e MYSQL_PASSWORD=app123 -v task-mysql-data:/var/lib/mysql mysql:8.0

Then:

docker exec -it task-mysql mysql -uappuser -papp123 taskdb

Run:

SELECT * FROM tasks;

Your old task should still exist.

----

Improve the Dockerfile

Now that the basic version works, let's make the Dockerfile slightly cleaner:

"""
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY database.py .

EXPOSE 5000

CMD ["python", "app.py"]

"""


Why?
PYTHONDONTWRITEBYTECODE=1

prevents unnecessary .pyc files.

PYTHONUNBUFFERED=1

makes Python logs appear immediately, which is useful in Docker/Jenkins.



Docker
        ┌──────────────────────────┐
        │                          │
        │                          │
        │   ┌──────────────────┐   │
Browser ───►│task-python       │   |
        │   │Flask Python      |   |
        │   │                  │   |
        │   └────────┬─────────┘   │
        │            │             │
        │            │             │
        │     task-network         │
        │            │             │
        │            ▼             │
        │   ┌──────────────────┐   │
        │   │ task-mysql       │   │
        │   │                  │   │
        │   │ MySQL            │   │
        │   └────────┬─────────┘   │
        │            │             │
        │            ▼             │
        │    task-mysql-data       │
        │       (volume)           │
        │                          │
        └──────────────────────────┘

☐ Docker network task-network created

☐ Docker volume task-mysql-data created

☐ MySQL container running

☐ Python Dockerfile created

☐ Python Docker image built

☐ Python container running

☐ Both containers are on task-network

☐ localhost:5000 works

☐ /health shows database connected

☐ POST /tasks works

☐ GET /tasks works

☐ PUT /tasks/<id> works

☐ DELETE /tasks/<id> works

☐ Python can resolve task-mysql

☐ MySQL data survives container recreation

☐ .dockerignore created

☐ .env is NOT inside Docker image