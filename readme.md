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