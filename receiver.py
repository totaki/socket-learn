"""
Это сервер будет ожидать подключения, в него будем писать id запроса и писать в ответ только по истечении случайного
времени в районе от 5 до 10 секунд с шагом 1 секунду сообщение echo: {id запроса}
"""
import asyncio
import argparse
import random


def get_handler(int_max_delay: int):
    async def handler(reader, writer):
        print('Accept connection')
        while True:
            bs_data = await reader.read(100)
            str_message = bs_data.decode()
            int_sleep_time = random.randint(1, int_max_delay)
            print('from {} | sleep: {:>2}'.format(str_message, int_sleep_time))
            await asyncio.sleep(int_sleep_time)
            writer.write(b'echo: %s' % bs_data)
            await writer.drain()
    return handler


def main(int_max_delay: int):
    loop = asyncio.get_event_loop()
    try:
        obj_server = asyncio.start_server(get_handler(int_max_delay), '127.0.0.1', 8888, loop=loop)
        future_server = loop.run_until_complete(obj_server)
        loop.run_forever()
    except KeyboardInterrupt:
        future_server.close()
        loop.run_until_complete(future_server.wait_closed())
    finally:
        loop.close()


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('max_delay', type=int)
    namespace = argument_parser.parse_args()
    main(namespace.max_delay)
