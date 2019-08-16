import tornado.ioloop
import tornado.web
import random
from tornado.websocket import WebSocketHandler as TornadoWebSocketHandler
from tornado.tcpserver import TCPServer
from tornado.iostream import StreamClosedError
from tornado import gen


END_SYMBOL = b'#'
MAX_DELAY = 5


class Connections:
    def __init__(self):
        self._service_connections = {}
        self._client_connections = {}
        self._ws_connections = {}


class Service(TCPServer):
    async def handle_stream(self, stream, address):
        while True:
            try:
                data = await stream.read_until(END_SYMBOL)
                delay = random.randint(1, MAX_DELAY)
                await gen.sleep(delay)
                await stream.write(b'echo: %s' % data)
            except StreamClosedError:
                break


class WebSocketHandler(TornadoWebSocketHandler):
    pass



class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('ui/index.html')


if __name__ == "__main__":
    connections = Connections()
    service = Service()
    loop = tornado.ioloop.IOLoop.current()
    application = tornado.web.Application([
        (r'/', MainHandler),
        (r'/ws', WebSocketHandler),
        (r'/static', tornado.web.StaticFileHandler),
    ], debug=True, connections=connections, static_path='ui/static')
    application.listen(8888)
    service.listen(9999)
    loop.start()
