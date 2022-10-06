import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS


# config
SQLALCHEMY_TRACK_MODIFICATIONS = True
app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://krupko_space:IGNOMINY-envisage-godly@192.168.0.155:54327/krupko_space'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://krupko_space:sterhedsg45whes@192.168.0.158:54321/krupko_space'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)
CORS(app)

# database
import models.feeds
db.create_all()

# routes
import routes.feeds

# run app
app.run('127.0.0.1', port=30010, debug=True)
