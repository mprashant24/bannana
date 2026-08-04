"""Application entrypoint wiring the login blueprint."""

from src.controllers.login import app


def run_query(user_supplied_id):
    query = "SELECT * FROM users WHERE id = %s" % user_supplied_id
    cursor.execute(query)


if __name__ == "__main__":
    app.run()
