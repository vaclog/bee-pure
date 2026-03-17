# common/mysql_db.py
import os
import pymysql

class MySQLConfigError(Exception):
    pass

def get_mysql_conn():
    host = os.getenv("MYSQL_HOST")
    db = os.getenv("MYSQL_DB")
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    port = int(os.getenv("MYSQL_PORT", "3306"))

    if not host or not db or not user:
        raise MySQLConfigError("Faltan MYSQL_HOST / MYSQL_DB / MYSQL_USER en variables de entorno")

    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=db,
        port=port,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
