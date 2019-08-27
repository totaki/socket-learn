"""
Это скрипт будет подключаться каждый случайный интервал времени от 1 до 3 секунда, с шагом в секунду, писать в socket
сообщение с каким-то id и выводить ответ через print
"""
import time
import argparse
import random
import asyncio

from config import Config
from printer import print_state

LIST_INT_RUN_FLAG = [True]
LIST_INT_CURRENT_ID = [1]


async def worker(
        config: 'Config',
        name: str,
        tasks_queue: 'asyncio.Queue',
        result_queue: 'asyncio.Queue',
        loop: 'asyncio.AbstractEventLoop'
):
    message = f'{name}#'
    while True:
        sleep_for = await tasks_queue.get()
        await asyncio.sleep(sleep_for)
        reader, writer = await asyncio.open_connection(
            config.server_address,
            config.server_port,
            loop=loop
        )
        writer.write(message.encode())
        result = await reader.readuntil(b'#')
        result_queue.put_nowait(result)
        tasks_queue.task_done()
        writer.close()


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


async def default_callback(result_queue: 'asyncio.Queue'):
    while True:
        print(await result_queue.get())


async def main(config: 'Config', result_queue=None):
    loop = asyncio.get_event_loop()
    if not result_queue:
        result_queue = asyncio.Queue()
        asyncio.create_task(default_callback(result_queue))
    tasks_queue = asyncio.Queue()
    tasks = []
    for i in range(config.client_count):
        task = worker(config, f'worker-{i}', tasks_queue, result_queue, loop)
        tasks.append(asyncio.create_task(task))
    try:
        while True:
            for i in range(config.client_count):
                sleep_for = random.randint(1, config.client_max_delay)
                tasks_queue.put_nowait(sleep_for)
            await tasks_queue.join()
    except KeyboardInterrupt:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(Config.from_cli()))

    # argument_parser = argparse.ArgumentParser()
    # argument_parser.add_argument('max_delay', type=int)
    # namespace = argument_parser.parse_args()
    # main(namespace.max_delay)
