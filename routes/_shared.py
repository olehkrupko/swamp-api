import json

from flask import Response, request


def data_is_json(func):
    def inner(*args, **kwargs):
        if not request.is_json:
            return Response(
                response=json.dumps({
                    "response": "Data is not JSON"
                }),
                status=400,
                mimetype='application/json'
            )

        func(*args, **kwargs)

    return inner


def return_json(response, status=200):
    return Response(
        response=json.dumps(
            obj=response,
            indent=4,
            sort_keys=True,
            default=str,
        ),
        status=status,
        mimetype='application/json'
    )
