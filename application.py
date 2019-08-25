import json
import logging

import tornado.ioloop
import tornado.web
import random
from tornado.websocket import WebSocketHandler as TornadoWebSocketHandler
from tornado.tcpserver import TCPServer
from tornado.iostream import StreamClosedError
from tornado import gen
from config import Config


END_SYMBOL = b'#'
MAX_DELAY = 5
WS_CONNECTIONS = set()
SERVER_CONNECTIONS = set()
SERVER_ADD = 'add'
SERVER_REMOVE = 'remove'


def write_message(conn, name: str, **kwargs) -> None:
    message = json.dumps({
        'name': name,
        'data': kwargs
    })
    try:
        conn.write_message(message)
    except Exception as e:
        logging.error('Write ws connection message error: %s', e)


def on_ws_client_connection(conn):
    write_message(conn, name='connected')
    for address in SERVER_CONNECTIONS:
        write_message(conn, 'server_%s' % SERVER_ADD, address=address[0], port=address[1])


def on_server_change(address, attr):
    getattr(SERVER_CONNECTIONS, attr)(address)
    for conn in WS_CONNECTIONS:
        write_message(conn, 'server_%s' % attr, address=address[0], port=address[1])


class Connections:
    def __init__(self):
        self._service_connections = {}
        self._client_connections = {}
        self._ws_connections = {}


class Service(TCPServer):
    async def handle_stream(self, stream, address):
        on_server_change(address, SERVER_ADD)
        while True:
            try:
                data = await stream.read_until(END_SYMBOL)
                delay = random.randint(1, MAX_DELAY)
                await gen.sleep(delay)
                await stream.write(b'echo: %s' % data)
            except StreamClosedError:
                break
        on_server_change(address, SERVER_REMOVE)


class WebSocketHandler(TornadoWebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self, *args: str, **kwargs: str) -> None:
        on_ws_client_connection(self)
        WS_CONNECTIONS.add(self)

    def close(self, code: int = None, reason: str = None) -> None:
        WS_CONNECTIONS.remove(self)


class MainHandler(tornado.web.RequestHandler):

    def get(self):
        config: 'Config' = self.settings['config']
        self.render(
            'ui/index.html',
            application_port=config.application_port,
            application_address=config.application_address
        )


if __name__ == "__main__":
    connections = Connections()
    service = Service()
    conf = Config.from_cli()
    application = tornado.web.Application([
        (r'/', MainHandler),
        (r'/ws', WebSocketHandler),
        (r'/static', tornado.web.StaticFileHandler),
    ], debug=True, connections=connections, static_path='ui/static', config=conf)

    loop = tornado.ioloop.IOLoop.current()
    application.listen(conf.application_port)
    service.listen(conf.service_port)
    loop.start()
