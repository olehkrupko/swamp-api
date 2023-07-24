import os
import sys

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS


# config
sys.dont_write_bytecode = True  # avoid writing __pycache__ and .pyc
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://krupko_space:IGNOMINY-envisage-godly@192.168.0.155:54327/krupko_space'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://krupko_space:sterhedsg45whes@192.168.0.158:54321/krupko_space'
FREQUENCIES = (
    'minutes',
    'hours',
    'days',
    'weeks',
    'months',
    'years',
    'never',
)

# database
db = SQLAlchemy(app)
import models.model_feeds
with app.app_context():
    db.create_all()

# routes
CORS(app)
import routes.route_feeds

# run app
if __name__ == '__main__':
    app.run('0.0.0.0', port=30010, debug=True)
