import json

from __main__ import app, db, FREQUENCIES


def data_is_json(func):
    def inner(*args, **kwargs):
        if not request.is_json:
            return app.response_class(
                response=json.dumps({
                    "response": "Data is not JSON"
                }),
                status=400,
                mimetype='application/json'
            )

        func(*args, **kwargs)

    return inner

def return_json(response, status=200):
    return app.response_class(
        response=json.dumps(
            obj=response,
            indent=4,
            sort_keys=True,
            default=str,
        ),
        status=status,
        mimetype='application/json'
    )
