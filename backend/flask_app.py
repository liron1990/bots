from app.webapp.flask_app import flask_app as app

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
