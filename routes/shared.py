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
