from django.db import DatabaseError, connection
from ninja import NinjaAPI, Schema, Status

api = NinjaAPI(title="MAPPA CFO", version="2.0")


class HealthOut(Schema):
    status: str


@api.get("/health", auth=None, response={200: HealthOut, 503: HealthOut})
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return Status(503, {"status": "indisponivel"})
    return Status(200, {"status": "ok"})
