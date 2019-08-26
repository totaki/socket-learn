"""
Это скрипт будет подключаться каждый случайный интервал времени от 1 до 3 секунда, с шагом в секунду, писать в socket
сообщение с каким-то id и выводить ответ через print
"""
import time
import argparse
import random
import asyncio
from printer import print_state

LIST_INT_RUN_FLAG = [True]
LIST_INT_CURRENT_ID = [1]


async def tcp_client(int_max_delay: int, int_id: int, event_loop: 'asyncio.AbstractEventLoop'):
    await asyncio.sleep(random.randint(1, int_max_delay))
    str_message = '{:0>4}#'.format(int_id)
    int_current_time = int(time.time())
    print_state('client_conn', str_message)
    obj_reader, obj_writer = await asyncio.open_connection('127.0.0.1', 8000, loop=event_loop)
    obj_writer.write(str_message.encode())
    print_state('client_wait', str_message)
    b_data = await obj_reader.read(100)
    print_state('client_recv', str_message, b_data.decode(), int(time.time()) - int_current_time)
    obj_writer.close()


async def run_clients_loop(event_loop: 'asyncio.AbstractEventLoop', int_max_delay: int):
    while LIST_INT_RUN_FLAG[0]:
        int_id = LIST_INT_CURRENT_ID[0]
        # Короче тут мы прекращаем выполнение и ждем когда задача закончится. Надо сделать по настоящему асинхронно
        event_loop.call_soon(lambda: asyncio.create_task(tcp_client(int_max_delay, int_id, event_loop)))
        LIST_INT_CURRENT_ID[0] += 1
        await asyncio.sleep(1)


def main(int_max_delay: int):
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_clients_loop(loop, int_max_delay=int_max_delay))
    except KeyboardInterrupt:
        LIST_INT_RUN_FLAG[0] = False
        tasks = asyncio.all_tasks(loop)
        loop.run_until_complete(asyncio.gather(*tasks))
    finally:
        loop.close()


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('max_delay', type=int)
    namespace = argument_parser.parse_args()
    main(namespace.max_delay)
