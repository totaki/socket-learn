import asyncio
import json
import logging
from typing import Union, Optional, Awaitable

import tornado.ioloop
import tornado.web
import random
from lib.client import main as clients_start
from tornado.websocket import WebSocketHandler as TornadoWebSocketHandler
from tornado.tcpserver import TCPServer
from tornado.iostream import StreamClosedError
from tornado.queues import Queue
from tornado import gen
from lib.config import Config


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


def on_message(message, delay, port):
    for conn in WS_CONNECTIONS:
        write_message(conn, 'server_send', message=message, delay=delay, port=port)


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
                on_message(data.decode()[:-1], delay, address[1])
                await gen.sleep(delay)
                await stream.write(b'handled#')
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

    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        if message == 'start':
            loop = asyncio.get_event_loop()
            asyncio.create_task(clients_start(self.settings['config'], loop, self.settings['result_queue']))


class MainHandler(tornado.web.RequestHandler):

    def get(self):
        config: 'Config' = self.settings['config']
        self.render(
            'ui/index.html',
            application_port=config.application_port,
            application_address=config.application_address
        )


def get_consumer(queue):
    async def _():
        async for item in queue:
            try:
                for conn in WS_CONNECTIONS:
                    name, *args = item[:-1].split(',')
                    write_message(conn, name, args=args)
            finally:
                queue.task_done()
    return _


if __name__ == "__main__":
    connections = Connections()
    result_queue = Queue()
    consumer = get_consumer(result_queue)
    service = Service()
    conf = Config.from_cli()
    loop = tornado.ioloop.IOLoop.current()
    application = tornado.web.Application([
        (r'/', MainHandler),
        (r'/ws', WebSocketHandler),
        (r'/static', tornado.web.StaticFileHandler),
    ],
        debug=True,
        connections=connections,
        static_path='ui/static',
        config=conf,
        result_queue=result_queue,
        loop=loop
    )
    loop.add_callback(consumer)
    application.listen(conf.application_port)
    service.listen(conf.service_port)
    loop.start()
