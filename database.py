import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(override=False)

def get_connection():
    # 1. Fetch values
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")

    # 2. Hard override if it defaults to localhost inside Docker
    if host in [None, "127.0.0.1", "localhost"]:
        host = "task-mysql"
        port = 3306
        user = "appuser"
        password = "app123"
        database = "taskdb"

    return mysql.connector.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database
    )
