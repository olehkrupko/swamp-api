from flask import request, Blueprint

import routes._shared as shared
from config.db import db
from models.model_feeds import Feed
from models.model_updates import Update


router = Blueprint("updates", __name__, url_prefix="/updates")


@router.route("/", methods=["GET"])
def list_updates():
    kwargs = dict(request.args)

    updates = Update.get_updates(**kwargs)

    return shared.return_json(
        response=updates,
    )
