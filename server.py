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
import socket
import select

list_out_connections = []
dict_in_connections = {}
dict_requests = {}
dict_responses = {}


def main():
    """
    EPOLLIN 1
    EPOLLOUT 4
    EPOLLHUP 16
    """
    EOL2 = b'\n\r\n'

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8080))
    server_socket.listen(1)
    server_socket.setblocking(0)
    server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    epoll = select.epoll(100)
    epoll.register(server_socket.fileno(), select.EPOLLIN)
    try:
        connections = {}; requests = {}; responses = {}
        while True:
            events = epoll.poll(0)
            for fileno, event in events:
                print(event, fileno)
                if fileno == server_socket.fileno():
                    connection, address = server_socket.accept()
                    connection.setblocking(0)
                    epoll.register(connection.fileno(), select.EPOLLIN)
                    connections[connection.fileno()] = connection
                    requests[connection.fileno()] = b''
                    responses[connection.fileno()] = b'busy: '
                elif event & select.EPOLLIN:

                    obj_connection = connections[fileno]
                    # Тут мы специальн читаем по 2 байта чтобы показать, что можем вычитывать не все за раз
                    bs_data = obj_connection.recv(2)
                    responses[obj_connection.fileno()] += bs_data
                    if len(responses[obj_connection.fileno()]) == 10:
                        epoll.modify(fileno, select.EPOLLOUT)

                elif event & select.EPOLLOUT:
                    byteswritten = connections[fileno].send(responses[fileno])
                    responses[fileno] = responses[fileno][byteswritten:]
                    if len(responses[fileno]) == 0:
                        epoll.modify(fileno, 0)
                        connections[fileno].shutdown(socket.SHUT_RDWR)
                elif event & select.EPOLLHUP:
                    epoll.unregister(fileno)
                    connections[fileno].close()
                    del connections[fileno]
    finally:
        epoll.unregister(server_socket.fileno())
        epoll.close()
        server_socket.close()


if __name__ == '__main__':
    main()
