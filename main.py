from venv import create
from flaskr.controllers import create_app

app = create_app()

if __name__ == '__main__':
    # Turn debug to True when working on features.
    app.run(debug=False)