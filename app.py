import time

from flask import Flask, request, jsonify, g, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from database import get_connection

app = Flask(__name__)

# Total HTTP requests, grouped by method, route, and status code
HTTP_REQUESTS_TOTAL = Counter(
    "flask_http_requests_total",
    "Total number of HTTP requests",
    ["method", "route", "status"]
)

# Time taken to process HTTP requests, in seconds
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "flask_http_request_duration_seconds",
    "HTTP request processing duration in seconds",
    ["method", "route"]
)

@app.before_request
def start_request_timer():
    # Do not include Prometheus scraping requests in application metrics
    if request.path == "/metrics":
        return

    g.request_start_time = time.perf_counter()


@app.after_request
def record_request_metrics(response):
    # Avoid counting Prometheus's own scraping requests
    if request.path == "/metrics":
        return response

    start_time = getattr(g, "request_start_time", None)

    if start_time is not None:
        route = request.url_rule.rule if request.url_rule else "unmatched"
        method = request.method
        status = str(response.status_code)

        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            route=route,
            status=status
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            route=route
        ).observe(time.perf_counter() - start_time)

    return response




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
@app.route("/metrics")
def metrics():
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )