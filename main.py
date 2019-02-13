import socket
import select
"""
   Типичная  архитектура приложения, использующего epoll, (сетевая часть)
   описана   ниже.   Такая   архитектура  позволяет  достичь  практически
   неограниченной масштабируемости на одно- и многопроцессорных системах:


     * Listener - поток, выполняющий вызовы bind() и listen() и слушающий
       входящий  сокет  в  ожидании  входящих  соединений. Когда приходит
       новое  соединение,  этот  потокделает  вызов accept() на слушающем
       сокете и отправляет полученный сокет соединения к I/O-workers.


     * I/O-Worker(s)  - один или несколько потоков, получающих соединения
       от  listener  и добавляющих их в epoll. Главный цикл таких потоков
       может  выглядеть  как  цикл,  описанный  в последнем шагу паттерна
       использования epoll(), описанном выше.


     * Data  Processing  Worker(s)  -  один  или  несколько  потоков  для
       получения   и   отправки  данных  для  I/O-workers  и  выполняющих
       обработку данных.
"""

response_text = '{"accounts": []}'
response_items = [
    'HTTP/1.1 200 OK',
    'Server: my-lol-server',
    'Content-Type: application/json; charset=utf-8',
    'Content-Length: %s' % len(response_text.encode()),
    '',
    response_text,
    ''
]
response = '\r\n'.join(response_items).encode()


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
                if fileno == server_socket.fileno():
                    connection, address = server_socket.accept()
                    connection.setblocking(0)
                    epoll.register(connection.fileno(), select.EPOLLIN)
                    connections[connection.fileno()] = connection
                    requests[connection.fileno()] = b''
                    responses[connection.fileno()] = response
                elif event & select.EPOLLIN:
                    requests[fileno] = connections[fileno].recv(1024)
                    if EOL2 in requests[fileno]:
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
