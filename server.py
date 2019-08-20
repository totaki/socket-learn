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
from typing import TYPE_CHECKING
import socket
import select
from printer import print_state


if TYPE_CHECKING:
    from select import epoll

list_out_connections = []
dict_polled_connections = {}
dict_in_connections = {}
dict_requests = {}
dict_responses = {}


class Services:
    def __init__(self, poll: 'epoll', address: str, port: int, count: int):
        self._poll = poll
        self._address = address
        self._port = port
        self._count = count
        self._connections = []
        self._acquired_connections = {}

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

    def return_connection(self):
        self._connections.append(
            self._acquired_connections.pop())


class Clients:
    def __init__(self, poll: 'epoll'):
        self._poll = poll

    def accept_client(self):
        pass

    def read_message(self):
        pass

    def write_message(self):
        pass

    def close_client(self):
        pass


class Server:
    def __init__(self, poll: 'epoll', port: int):
        self._poll = poll
        self._port = port


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


if __name__ == '__main__':
    main()
