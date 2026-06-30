from flask_mysqldb import MySQL

def init_db(app):
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'root'
    app.config['MYSQL_DB'] = 'Tastyhub'
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    # Optional: connection timeout / cursor class etc.
    mysql = MySQL(app)
    return mysql
