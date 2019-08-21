"""
Это будет наш главный тестовый сервер, мы будет обрабатывать подключения у нас булет pool соединений состоящий из
2-х к receiver, все подключения которые не смогли себе забрать будем отдавать busy: {id запроса}
Попробую описать принцип работы.
Мы создаем объект epoll регистрируем в нем 3 сокета
- 1 на чтение.
- 2 на запись. (вопрос тут такой у нас каждый раз будет срабатывать собитие на запись, или нам надо только когда пришли
данные зарегистрировать его на запись, проверим заодно)
Мы в цикле опрашиваем наши эвенты, как только пришло входящее соединение мы accept и регистрируем его на чтение. Когда
пришли по нему данные мы смотрим есть ли у нас свободнное подключение к нашей фейковой бд, если есть мы его забираем
пишем туда данные (возможно нужна регистрация на запись) и ждем. Если свободного нет отдаем ответ и закрываем соединение
Когда приходить ответ от фейкового сервера БД, мы отвечаем в нужные сокет и возвращаем в наш пул.
"""
from typing import TYPE_CHECKING, List, Dict, Union
import socket
import select
import json

from printer import print_state

if TYPE_CHECKING:
    from select import epoll
    from socket import socket as sock
    from typing import Tuple

Int = Union[str, int]

list_out_connections = []
dict_polled_connections = {}
dict_in_connections = {}
dict_requests = {}
dict_responses = {}


def pprint(key, value: str = ''):
    print(' {0: >36} = 1'.format(key, value))


class Config:
    def __init__(self,
                 server_address: str,
                 server_port: Int,
                 service_address: str,
                 service_port: Int,
                 service_conn_count: Int,
                 poll_wait: Int,
                 size_hint: Int,
                 ):
        self.server_address = server_address
        self.server_port = server_port
        self.service_address = service_address
        self.service_port = service_port
        self.service_conn_count = service_conn_count
        self.poll_wait = poll_wait
        self.size_hint = size_hint

    @classmethod
    def load(cls, file_name: str) -> 'Config':
        with open(file_name) as f:
            _config = json.load(f)
            print('\nLoad config:')
            for k in sorted(_config):
                print_key = ' '.join(k.split('_')).capitalize()
                print(f'    {print_key}: {_config[k]}')
            return cls(**_config)


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


class Clients:
    def __init__(self):
        pass

    def accept_client(self):
        pass

    def read_message(self):
        pass

    def write_message(self):
        pass

    def close_client(self):
        pass


class Server:
    def __init__(self, config: Config):
        self._config: Config = config
        self._clients: Dict[int, Client] = {}
        self._services: Services = Services(self._config)
        self._poll: 'epoll' = select.epoll(self._config.poll_wait)
        self._socket: 'sock' = self._get_socket()

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
        self._poll = select.epoll(self._config.size_hint)
        self._poll.register(self._socket.fileno(), select.EPOLLIN)
        self._services.connect()
        pprint('SERVER SETUP')

    def accept_client(self):
        connection, address = self._socket.accept()  # type: sock, Tuple[str, int]
        client = Client(*address, connection=connection)
        connection.setblocking(False)
        self._clients[connection.fileno()] = client
        self._poll.register(connection.fileno(), select.EPOLLIN)
        pprint('CLIENT_CONNECTED', '{}:{}'.format(*address))

    def get_client(self, s: 'sock') -> Client:
        return self._clients[s.fileno()]


def get_connection():
    obj_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    obj_socket.connect(('localhost', 8888))
    obj_socket.setblocking(0)
    obj_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return obj_socket


def main():
    """
    EPOLLIN 1
    EPOLLOUT 4
    EPOLLHUP 16
    """

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8080))
    server_socket.listen(1)
    server_socket.setblocking(0)
    server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    epoll = select.epoll(100)
    epoll.register(server_socket.fileno(), select.EPOLLIN)
    print_state('srv_reg_in_server', server_socket.fileno())
    list_out_connections.extend([get_connection() for i in range(2)])
    try:
        while True:
            events = epoll.poll(0)
            for fileno, event in events:
                if fileno == server_socket.fileno():
                    connection, address = server_socket.accept()
                    connection.setblocking(0)
                    epoll.register(connection.fileno(), select.EPOLLIN)
                    print_state('srv_reg_in_cl', connection.fileno())
                    dict_in_connections[connection.fileno()] = connection
                    dict_requests[connection.fileno()] = b''
                    dict_responses[connection.fileno()] = b'busy: '

                elif event & select.EPOLLIN:
                    if fileno in dict_polled_connections:
                        print_state('srv_recv_from_db', fileno)
                        dict_request_data = dict_polled_connections.pop(fileno)
                        bs_data = dict_request_data['conn'].recv(10)
                        dict_responses[dict_request_data['fileno']] = bs_data
                        # Изменяем регистрацию клиентского сокета на выход
                        print_state('srv_reg_out_cl', dict_request_data['fileno'])
                        epoll.modify(dict_request_data['fileno'], select.EPOLLOUT)

                        # Уберем регистрацию для db сокета
                        print_state('srv_unreg_db', fileno)
                        epoll.unregister(fileno)

                        # Вернем наш сокет в poll
                        print_state('srv_push_to_pull_db', fileno)
                        list_out_connections.append(dict_request_data['conn'])
                    else:
                        obj_connection = dict_in_connections[fileno]
                        # Тут мы специальн читаем по 2 байта чтобы показать, что можем вычитывать не все за раз
                        bs_data = obj_connection.recv(2)
                        print_state('srv_recv_from_cl', fileno, bs_data.decode())
                        dict_responses[obj_connection.fileno()] += bs_data
                        if len(dict_responses[obj_connection.fileno()]) == 10:
                            if len(list_out_connections):
                                # Забираем одно подкючение ставим его на out, добавляем в словарь для отсылки данных
                                # вместе с даннами и туда же кладем конект в который потом надо написать.
                                connection = list_out_connections.pop()
                                dict_polled_connections[connection.fileno()] = {
                                    'data': dict_responses[obj_connection.fileno()][6:],
                                    'fileno': obj_connection.fileno(),
                                    'conn': connection
                                }
                                print_state(
                                    'srv_reg_out_db',
                                    fileno,
                                    dict_responses[obj_connection.fileno()][6:].decode()
                                )
                                epoll.register(connection.fileno(), select.EPOLLOUT)
                            else:
                                # Если подключений нет отправляем busy
                                print_state(
                                    'srv_reg_out_cl',
                                    fileno,
                                    dict_responses[obj_connection.fileno()].decode()
                                )
                                epoll.modify(fileno, select.EPOLLOUT)

                elif event & select.EPOLLOUT:
                    # Проверяем если мы сокет в готовых к посылке данных сокатаъ
                    if fileno in dict_polled_connections:

                        print_state('srv_send_to_db', fileno, dict_polled_connections[fileno]['data'].decode())
                        dict_polled_connections[fileno]['conn'].send(dict_polled_connections[fileno]['data'])

                        print_state('srv_reg_in_db', fileno)
                        epoll.modify(fileno, select.EPOLLIN)
                    else:
                        print_state('srv_send_cl', fileno, dict_responses[fileno].decode())
                        byteswritten = dict_in_connections[fileno].send(dict_responses[fileno])
                        dict_responses[fileno] = dict_responses[fileno][byteswritten:]
                        if len(dict_responses[fileno]) == 0:
                            print_state('srv_reg_0_cl', fileno)
                            epoll.modify(fileno, 0)

                            print_state('srv_shutdown_cl', fileno)
                            dict_in_connections[fileno].shutdown(socket.SHUT_RDWR)

                elif event & select.EPOLLHUP:
                    print_state('srv_unreg_cl', fileno)
                    epoll.unregister(fileno)
                    print_state('srv_close_cl', fileno)
                    dict_in_connections[fileno].close()
                    del dict_in_connections[fileno]
    finally:
        epoll.unregister(server_socket.fileno())
        epoll.close()
        server_socket.close()


def _main(config: 'Config'):
    pass


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--config', default='config.json', required=False)
    args = parser.parse_args()
    _main(Config.load(args.config))
