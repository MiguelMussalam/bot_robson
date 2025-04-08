import json
from main import interact

def lambda_handler(event, context):
    # A função lambda espera que o corpo da requisição venha como string JSON
    try:
        body = json.loads(event["body"])
    except (KeyError, json.JSONDecodeError):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Requisição malformada"})
        }

    # Aqui o evento do Discord é processado pela função interact
    response = interact(body)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(response)
    }