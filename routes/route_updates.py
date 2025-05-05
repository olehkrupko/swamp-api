from os import getenv

from flask import request, Blueprint

import routes._shared as shared
from models.model_updates import Update


router = Blueprint("updates", __name__, url_prefix="/updates")


@router.route("/", methods=["GET"])
def list_updates():
    kwargs = dict(request.args)
    if getenv("MODE") == "PUBLIC":
        kwargs["private"] = False

    updates = Update.get_updates(**kwargs)

    return shared.return_json(
        response=updates,
    )


@router.route("/parse/", methods=["GET"])
def parse_updates():
    body = request.args
    href = body["href"]

    response = Update.parse_href(href)

    return shared.return_json(
        response=response,
    )
