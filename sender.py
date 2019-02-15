"""
Это скрипт будет подключаться каждый случайный интервал времени от 1 до 3 секунда, с шагом в секунду, писать в socket
сообщение с каким-то id и выводить ответ через logging
"""
import argparse
import random
import asyncio


async def tcp_echo_client(message, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888,
                                                   loop=loop)

    print('Send: %r' % message)
    writer.write(message.encode())

    data = await reader.read(100)
    print('Received: %r' % data.decode())

    print('Close the socket')
    writer.close()


def main(int_max_delay: int):
    message = 'Hello World!'
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tcp_echo_client(message, loop))
    loop.close()


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('max_delay', type=int)
    namespace = argument_parser.parse_args()
    main(namespace.max_delay)
