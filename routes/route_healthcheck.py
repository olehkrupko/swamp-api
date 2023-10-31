import routes._shared as shared

from __main__ import app


ROUTE_PATH = "/healthcheck"


@app.route(f"{ ROUTE_PATH }/", methods=['GET'])
def healthcheck():
    return shared.return_json(
        response=True,
    )
