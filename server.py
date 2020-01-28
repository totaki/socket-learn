from typing import TYPE_CHECKING, List, Dict, Optional
import socket
import select

from lib.config import Config

if TYPE_CHECKING:
    from select import epoll
    from socket import socket as sock
    from typing import Tuple


READ_BYTES = 4


def pprint(key, value: str = ''):
    print(' {0: >36} = {1}'.format(key, value))


class Services:
    def __init__(self, config: 'Config'):
        self._address = config.service_address
        self._port = config.service_port
        self._count = config.service_conn_count
        self._connections: List['sock'] = []

    def connect(self):
        for i in range(self._count):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self._address, self._port))
            s.setblocking(False)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._connections.append(s)

    def write_message(self):
        pass

    def read_message(self):
        pass

    def acquire(self):
        if len(self._connections):
            return self._connections.pop()
        else:
            return None

    def return_connection(self, s: 'sock'):
        self._connections.append(s)


class Client:
    def __init__(self,
                 address: str,
                 port: int,
                 connection: 'sock',
                 read_bytes: bytes = b'',
                 write_bytes: bytes = b'',
                 ):
        self.address = address
        self.port = port
        self.read_bytes = read_bytes
        self.write_bytes = write_bytes
        self.connection = connection


class Server:
    def __init__(self, config: Config):
        self._config: Config = config
        self._clients: Dict[int, Client] = {}
        self._services: Services = Services(self._config)
        self._wait_clients: Dict[int, Tuple['sock', Client]] = {}
        self._poll: Optional['epoll'] = None
        self._socket: Optional['sock'] = None

    @property
    def fn(self):
        return self._socket.fileno()

    def _get_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((
            self._config.service_address,
            self._config.server_port
        ))
        s.listen(1)
        s.setblocking(False)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return s

    def setup(self):
        try:
            self._poll = select.epoll(self._config.size_hint)
            self._socket = self._get_socket()
            self._poll.register(self._socket.fileno(), select.EPOLLIN)
            self._services.connect()
            pprint('SERVER SETUP')
        except Exception:
            self.stop()
            raise

    def accept_client(self):
        connection, address = self._socket.accept()  # type: sock, Tuple[str, int]
        client = Client(*address, connection=connection)
        connection.setblocking(False)
        self._clients[connection.fileno()] = client
        self._poll.register(connection.fileno(), select.EPOLLIN)
        pprint('CLIENT_CONNECTED', '{}:{}'.format(*address))

    def handle_incoming_event(self, fn: int):
        pprint('INCOMING DATA')
        if fn in self._wait_clients:
            service_conn, cl = self._wait_clients[fn]
            cl.write_bytes += service_conn.recv(READ_BYTES)
            if cl.write_bytes.endswith(b'#'):
                pprint('BYTES FROM SERVICE', cl.write_bytes.decode())
                self._poll.unregister(fn)
                self._services.return_connection(service_conn)
                self._wait_clients.pop(fn)
                self._poll.modify(cl.connection.fileno(), select.EPOLLOUT)
        else:
            cl = self._clients[fn]
            cl.read_bytes += cl.connection.recv(READ_BYTES)
            if cl.read_bytes.endswith(b'#'):
                pprint('BYTES FROM CLIENT', cl.read_bytes.decode())
                service_conn = self._services.acquire()
                if service_conn:
                    self._wait_clients[service_conn.fileno()] = (service_conn, cl)
                    self._poll.register(service_conn.fileno(), select.EPOLLOUT)
                else:
                    cl.write_bytes += b'service_busy#'
                    self._poll.modify(fn, select.EPOLLOUT)

    def handle_outgoing_event(self, fn: int):
        pprint('OUTGOING DATA')
        if fn in self._wait_clients:
            service_conn, cl = self._wait_clients[fn]
            message = f'{cl.address},{cl.port},{cl.read_bytes.decode()}'
            service_conn.send(message.encode())
            self._poll.modify(service_conn.fileno(), select.EPOLLIN)
        else:
            cl = self._clients[fn]
            cl.connection.send(cl.write_bytes)
            self._poll.modify(fn, 0)
            cl.connection.shutdown(socket.SHUT_RDWR)

    def handle_close_event(self, fn: int):
        client = self._clients[fn]
        self._poll.unregister(fn)
        client.connection.close()
        pprint('CLIENT_DISCONNECTED', '{}:{}'.format(client.address, client.port))
        del self._clients[fn]

    def get_client(self, s: 'sock') -> Client:
        return self._clients[s.fileno()]

    def get_event(self):
        return self._poll.poll(self._config.poll_wait)

    def stop(self):
        # TODO: более изящное решение, возможно добавить какой-то state бинарный или на каждое
        #  действие добавлять callback на отключение
        try:
            self._poll.unregister(self._socket.fileno())
        except:
            pass

        try:
            self._poll.close()
        except:
            pass

        try:
            self._socket.close()
        except:
            pass


def get_connection():
    obj_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    obj_socket.connect(('localhost', 8888))
    obj_socket.setblocking(0)
    obj_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return obj_socket


def main(config: 'Config'):
    server = Server(config)
    try:
        server.setup()
        while True:
            events = server.get_event()
            for fn, event in events:
                if fn == server.fn:
                    server.accept_client()
                elif event & select.EPOLLIN:
                    server.handle_incoming_event(fn)
                elif event & select.EPOLLOUT:
                    server.handle_outgoing_event(fn)
                elif event & select.EPOLLHUP:
                    pass
    finally:
        server.stop()


if __name__ == '__main__':
    main(Config.from_cli())
