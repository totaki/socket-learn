"""
Это скрипт будет подключаться каждый случайный интервал времени от 1 до 3 секунда, с шагом в секунду, писать в socket
сообщение с каким-то id и выводить ответ через print
"""
import time
import argparse
import random
import asyncio

LIST_INT_RUN_FLAG = [True]
LIST_INT_CURRENT_ID = [1]


async def tcp_echo_client(int_id: int, event_loop: 'asyncio.AbstractEventLoop'):
    float_start = time.time()
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888, loop=event_loop)
    message = '{:0>4}'.format(int_id)
    writer.write(message.encode())
    data = await reader.read(100)
    float_delta = time.time() - float_start
    print('{:>10.6f} | {:>10}'.format(float_delta, data.decode()))
    writer.close()


async def sender_loop(event_loop: 'asyncio.AbstractEventLoop', int_max_delay: int):
    while LIST_INT_RUN_FLAG[0]:
        int_id = LIST_INT_CURRENT_ID[0]
        await asyncio.create_task(tcp_echo_client(int_id, event_loop))
        LIST_INT_CURRENT_ID[0] += 1
        await asyncio.sleep(random.randint(1, int_max_delay))


def main(int_max_delay: int):
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(sender_loop(loop, int_max_delay=int_max_delay))
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
