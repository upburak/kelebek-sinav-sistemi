# Yalnızca bulut önizleme ortamı için ASGI adaptörü; yerel macOS/Windows çalışmasını etkilemez.
from a2wsgi import WSGIMiddleware

from kelebek import create_app

app = WSGIMiddleware(create_app())
