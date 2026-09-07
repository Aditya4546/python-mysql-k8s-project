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