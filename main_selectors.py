import selectors
import socket

"""
2.013869ms:/accounts/new/?query_id=1872
729.928µs:/accounts/new/?query_id=398
637.9µs:/accounts/new/?query_id=1717
513.808µs:/accounts/new/?query_id=1343
489.497µs:/accounts/new/?query_id=1340
451.975µs:/accounts/new/?query_id=7
442.439µs:/accounts/new/?query_id=743
347.041µs:/accounts/new/?query_id=1354
309.801µs:/accounts/new/?query_id=9067
305.759µs:/accounts/new/?query_id=3616

Короче тут такая же картина есть мега медленные запросы, такое ощущение что эвенты на них попадают в последнюю очередь
"""

sel = selectors.EpollSelector()

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


def accept(sock, mask):
    conn, addr = sock.accept()  # Should be ready
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, read)


def read(conn, mask):
    data = conn.recv(1024)  # Should be ready
    if data:
        conn.send(response)  # Hope it won't block
        sel.unregister(conn)
        conn.close()
    else:
        sel.unregister(conn)
        conn.close()


sock = socket.socket()
sock.bind(('0.0.0.0', 8080))
sock.listen(100)
sock.setblocking(False)
sel.register(sock, selectors.EVENT_READ, accept)


try:
    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)
except KeyboardInterrupt:
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()
