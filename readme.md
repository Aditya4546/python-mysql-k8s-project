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


LAB 3 — Move the Application to Kubernetes

Now we're going to replace the Docker-level orchestration with Kubernetes.

                         Kubernetes Cluster
┌──────────────────────────────────────────────────────────┐
│                                                          │
│                  ┌─────────────────┐                     │
│                  │ Python Service  │                     │
│                  └────────┬────────┘                     │
│                           │                              │
│                           ▼                              │
│                 ┌──────────────────┐                     │
│                 │   Python Pod     │                     │
│                 │                  │                     │
│                 │ Flask Application│                     │
│                 └────────┬─────────┘                     │
│                          │                              │
│                          │ mysql-service:3306           │
│                          ▼                              │
│                 ┌──────────────────┐                     │
│                 │ MySQL Service    │                     │
│                 └────────┬─────────┘                     │
│                          │                              │
│                          ▼                              │
│                 ┌──────────────────┐                     │
│                 │    MySQL Pod     │                     │
│                 │                  │                     │
│                 │      MySQL       │                     │
│                 └────────┬─────────┘                     │
│                          │                              │
│                          ▼                              │
│                 ┌──────────────────┐                     │
│                 │       PVC        │                     │
│                 │ Persistent Data  │                     │
│                 └──────────────────┘                     │
│                                                          │
└──────────────────────────────────────────────────────────┘

=========================================================================
What are we actually learning?

In LAB 3, we'll introduce

| Kubernetes concept    | What it does                |
| --------------------- | --------------------------- |
| Pod                   | Runs our container          |
| Deployment            | Manages application Pods    |
| Service               | Provides stable networking  |
| Secret                | Stores sensitive values     |
| ConfigMap             | Stores configuration        |
| PersistentVolumeClaim | Persistent database storage |
| Namespace             | Organizes resources         |



--------------------------------------------------------------
PART 1 — Check Kubernetes

Before doing anything, we need Kubernetes running locally.

Since you're using Docker Desktop, the easiest setup is Docker Desktop's built-in Kubernetes.

Open Docker Desktop.

Go to:

Settings → Kubernetes

Enable Kubernetes.

Depending on your Docker Desktop version, you'll see an option such as:

_Enable Kubernetes_

Apply/restart Docker Desktop.

Wait until Kubernetes shows as running.

------------------------------------------------
PART 2 Verify Kubernetes

Open a new Command Prompt or PowerShell.

Run:

kubectl version --client

Then:

kubectl get nodes

--------------------------------

If kubectl is not recognized

If you get:



'kubectl' is not recognized...

don't continue yet.

Docker Desktop normally provides kubectl, but your PATH may not be configured.

We'll fix that before proceeding.

----------------------------------

PART 3 — Create a project structure

Create:

kubernetes folder in your project,



-----------------------------------
PART 4 Understand the Kubernetes design


Python

We'll create:

Python Deployment
       ↓
Python Pod
       ↓
task-python-app

Initially:

replicas: 1

Later we can change:

replicas: 3

and Kubernetes will run:

Python Pod 1
Python Pod 2
Python Pod 3

This is where Kubernetes becomes much more powerful than our Docker setup.

---------------------------------------------------------------------   

MySQL

We'll create:

MySQL
  ↓
MySQL Pod
  ↓
Persistent Storage

For this lab, we'll start with one MySQL Pod.

Why?

Because MySQL is stateful.

We don't want to teach:

3 MySQL Pods

before explaining database replication, clustering, and state management.

----------------------------------------------------------------------


PART 5 — Create MySQL Secret


Create MySQL Secret

Inside:

kubernetes/

create:

mysql-secret.yaml

Put:

apiVersion: v1
kind: Secret

metadata:
  name: mysql-secret

type: Opaque

stringData:
  MYSQL_ROOT_PASSWORD: root123
  MYSQL_USER: appuser
  MYSQL_PASSWORD: app123
  MYSQL_DATABASE: taskdb

This contains:

MYSQL_ROOT_PASSWORD
MYSQL_USER
MYSQL_PASSWORD
MYSQL_DATABASE

Instead of putting passwords directly into the Deployment.
-----------------------------------------------------------------------

Secret vs .env

In LAB 2 we had:

.env

Now we're moving toward:

Kubernetes Secret

So:

LAB 2

.env
 ↓
Docker
 ↓
Python

becomes:

LAB 3

Kubernetes Secret
 ↓
Pod
 ↓
Python

This is a very important transition.
=================================================

PART 6 — Create MySQL storage


Create:

mysql-pvc.yaml

Put:

apiVersion: v1
kind: PersistentVolumeClaim

metadata:
  name: mysql-pvc

spec:
  accessModes:
    - ReadWriteOnce

  resources:
    requests:
      storage: 1Gi

---

We're requesting:

1 GB

of persistent storage.
-----------------------------------

Understand this

Without PVC:

MySQL Pod
   ↓
Database
   ↓
Pod deleted
   ↓
Potential data loss

With PVC:

MySQL Pod
   ↓
MySQL
   ↓
PVC
   ↓
Persistent Storage

Pod can disappear and Kubernetes can create another Pod using the same storage.

--------------------------------------
PART 7 — Create MySQL Deployment

Create:

mysql-deployment.yaml

Put:

apiVersion: apps/v1
kind: Deployment

metadata:
  name: mysql

spec:
  replicas: 1

  selector:
    matchLabels:
      app: mysql

  template:

    metadata:
      labels:
        app: mysql

    spec:

      containers:

        - name: mysql

          image: mysql:8.0

          ports:
            - containerPort: 3306

          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: MYSQL_ROOT_PASSWORD

            - name: MYSQL_DATABASE
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: MYSQL_DATABASE

            - name: MYSQL_USER
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: MYSQL_USER

            - name: MYSQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: MYSQL_PASSWORD

          volumeMounts:
            - name: mysql-storage
              mountPath: /var/lib/mysql

      volumes:
        - name: mysql-storage
          persistentVolumeClaim:
            claimName: mysql-pvc


-----------------------------------------------
What just happened?

We told Kubernetes:

Create one MySQL Pod using the mysql:8.0 image and mount persistent storage at /var/lib/mysql.

So:

Deployment
     ↓
MySQL Pod
     ↓
MySQL Container
     ↓
/var/lib/mysql
     ↓
mysql-pvc


---------------------------------------------------

PART 8 — Create MySQL Service

Now we need to solve the most important networking problem.

Create:

mysql-service.yaml

Put:

apiVersion: v1
kind: Service

metadata:
  name: mysql-service

spec:
  selector:
    app: mysql

  ports:
    - protocol: TCP
      port: 3306
      targetPort: 3306

Notice:

name: mysql-service

This is the hostname our Python application will use.

---------------------------------------------------------

This is the magic of Kubernetes

Our MySQL Pod might receive an IP like:

10.1.0.15

But tomorrow it could become:

10.1.0.28

Python shouldn't care.

Python simply uses:

mysql-service

Kubernetes DNS handles the rest.

Therefore:

Python Pod
    │
    │ mysql-service:3306
    ▼
MySQL Service
    │
    ▼
MySQL Pod

================================================

PART 9 — Deploy MySQL


Now we have four Kubernetes files:

kubernetes/
│
├── mysql-secret.yaml
├── mysql-pvc.yaml
├── mysql-deployment.yaml
└── mysql-service.yaml

Apply them.

First:

kubectl apply -f kubernetes/mysql-secret.yaml

Then:

kubectl apply -f kubernetes/mysql-pvc.yaml

Then:

kubectl apply -f kubernetes/mysql-deployment.yaml

Then:

kubectl apply -f kubernetes/mysql-service.yaml

Or all at once:

kubectl apply -f kubernetes/

We'll use the individual commands the first time, because you should see what each resource does.


-------------------------------------------------------------------


PART 10 — Check the Secret
kubectl get secrets

You should see:

mysql-secret

Don't use:

kubectl get secret mysql-secret -o yaml

and paste the output somewhere publicly, because it contains encoded secret data.

-------------------------------------------------------------------

PART 11 — Check PVC

Run:

kubectl get pvc

You want:

NAME        STATUS   VOLUME
mysql-pvc   Bound

The important word is:

Bound

If it's:

Pending

stop here and tell me.

----------------------------------------------------


PART 12 — Check the MySQL Pod

Run:

kubectl get pods

Initially you might see:

mysql-xxxxxxxxx-xxxxx   0/1   ContainerCreating

Wait a little.

Then:

mysql-xxxxxxxxx-xxxxx   1/1   Running

That's what we want.

-------------------------------------------------------------


PART 13 — Check the Deployment
kubectl get deployments

You should see:

NAME    READY   UP-TO-DATE   AVAILABLE
mysql   1/1     1            1



-------------------------------------------------
PART 14 — Check the Service
kubectl get services

You should see:

NAME            TYPE        CLUSTER-IP      PORT
mysql-service   ClusterIP   10.x.x.x        3306

The default Service type is:

ClusterIP

That's exactly what we want.

Why?

Because MySQL doesn't need to be exposed to your browser or the internet.

Only the Python application needs to communicate with it.

-----------------------------------------------------



PART 15 — Initialize the MySQL database

This is slightly different from Docker.

Our Kubernetes MySQL container starts with a fresh PVC.

We need to create:

taskdb
tasks

The taskdb database is already created by:

MYSQL_DATABASE: taskdb

But we need the table.

First find the Pod:

kubectl get pods

You'll see something like:

mysql-7d8f9c8d6b-x7abc

Now copy init.sql into the Pod:

kubectl cp init.sql mysql-pod-name:/init.sql

Replace the Pod name with your actual Pod name.

Then execute:

kubectl exec -it mysql-pod-name -- mysql -uappuser -papp123 taskdb -e "source /init.sql"

If successful, you should not get an SQL error.

Verify:

kubectl exec -it mysql-pod-name -- mysql -uappuser -papp123 taskdb -e "SHOW TABLES;"

You should see:

tasks

-------------------------------------------------------------------------


PART 16 — Now comes Python

This is where LAB 3 gets exciting.

We already have:

MySQL Pod

Now we'll create:

Python Pod

Create:

app-deployment.yaml

Put:

apiVersion: apps/v1
kind: Deployment

metadata:
  name: task-python

spec:
  replicas: 1

  selector:
    matchLabels:
      app: task-python

  template:

    metadata:
      labels:
        app: task-python

    spec:

      containers:

        - name: task-python

          image: task-python-app:latest

          imagePullPolicy: Never

          ports:
            - containerPort: 5000

          env:
            - name: DB_HOST
              value: mysql-service

            - name: DB_PORT
              value: "3306"

            - name: DB_USER
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: MYSQL_USER

            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: MYSQL_PASSWORD

            - name: DB_NAME
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: MYSQL_DATABASE



--------------------------------------------------------------------



PART 17 — Apply Python Deployment

Run:

kubectl apply -f kubernetes/app-deployment.yaml

Then:

kubectl get pods

You should eventually have:

mysql-xxxxxxxxx-xxxxx       1/1   Running
task-python-xxxxxxxxx-xxxxx 1/1   Running

🎉

You now have two application workloads running inside Kubernetes.
----------------------------------------------------------------------



PART 18 — Check Python logs

Run:

kubectl logs deployment/task-python

You want to see:

Running on http://0.0.0.0:5000


-----------------------------------------------------------------------------


PART 19 — Create Python Service

Create:

app-service.yaml

Put:

apiVersion: v1
kind: Service

metadata:
  name: task-python-service

spec:
  type: NodePort

  selector:
    app: task-python

  ports:
    - protocol: TCP
      port: 5000
      targetPort: 5000
      nodePort: 30050

Now:

Browser
   │
   │ :30050
   ▼
task-python-service
   │
   ▼
Python Pod
   │
   │ mysql-service:3306
   ▼
MySQL Service
   │
   ▼
MySQL Pod

---------------------------------------------

PART 20 — Apply the Python Service
kubectl apply -f kubernetes/app-service.yaml

Check:

kubectl get services

You should see:

mysql-service
task-python-service

----------------------------------------------------


PART 21 — Access the application

kubectl port-forward service/task-python-service 5000:5000


With Docker Desktop Kubernetes, try:

http://localhost:5000

You should get:

{
    "message": "Task Management API is running"
}

Then:

http://localhost:5000/health

Expected:

{
    "database": "connected",
    "status": "healthy"
}

🔥 This is the moment we want.

You have:

Browser
   ↓
Kubernetes Service
   ↓
Python Pod
   ↓
MySQL Service
   ↓
MySQL Pod
   ↓
Persistent Storage

---------------------------------------------------------

PART 22 — Test the API

Create a task:

POST http://localhost:5000/tasks
{
    "title": "Kubernetes Lab",
    "description": "Python communicating with MySQL through Kubernetes"
}

Then:

GET http://localhost:5000/tasks

You should see the task.

-----------------------------------------------------


PART 23 — The experiment I REALLY want you to perform

This demonstrates why Kubernetes is useful.

Find the Python Pod:

kubectl get pods

Then delete it:

kubectl delete pod <python-pod-name>

Immediately run:

kubectl get pods

You'll see the old Pod disappear and a new Pod appear.

Why?

Because:

Deployment
     ↓
"I need 1 Python Pod"
     ↓
Pod deleted
     ↓
Deployment notices
     ↓
Create replacement Pod

This is self-healing.

-----------------------------------------------------

PART 24 — Delete MySQL Pod

Now let's do the same thing to MySQL.

kubectl get pods

Delete the MySQL Pod:

kubectl delete pod <mysql-pod-name>

Watch:

kubectl get pods -w

Kubernetes will create a new MySQL Pod.

Then check:

kubectl get pvc

Your:

mysql-pvc

should still be:

Bound

This is why persistent storage matters.

---------------------------------------------------------

PART 25 — Verify the database survived

Once MySQL is running again:

kubectl get pods

Get the new MySQL Pod name.

Then:

kubectl exec -it <mysql-pod-name> -- mysql -uappuser -papp123 taskdb

Run:

SELECT * FROM tasks;

Your previous data should still be there.

That demonstrates:

Pod
 ↓
deleted
 ↓
new Pod
 ↓
same PVC
 ↓
same data
-----------------------------------------
