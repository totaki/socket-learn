"""
Это скрипт будет подключаться каждый случайный интервал времени от 1 до 3 секунда, с шагом в секунду, писать в socket
сообщение с каким-то id и выводить ответ через print
"""
import random
import asyncio
from config import Config


async def worker(
        config: 'Config',
        name: str,
        tasks_queue: 'asyncio.Queue',
        result_queue: 'asyncio.Queue',
        loop: 'asyncio.AbstractEventLoop'
):
    message = f'{name}#'
    result_queue.put_nowait(f'worker_ready,{message}')
    while True:
        sleep_for = await tasks_queue.get()
        result_queue.put_nowait(f'worker_wait_start,{sleep_for},{message}')
        await asyncio.sleep(sleep_for)
        reader, writer = await asyncio.open_connection(
            config.server_address,
            config.server_port,
            loop=loop
        )
        writer.write(message.encode())
        result_queue.put_nowait(f'worker_wait_result,{message}')
        result = await reader.readuntil(b'#')
        result_queue.put_nowait(f'worker_result,{result.decode()[:-1]},{message}')
        tasks_queue.task_done()
        writer.close()


async def default_callback(result_queue: 'asyncio.Queue'):
    while True:
        print(await result_queue.get())


async def main(config: 'Config', loop: 'asyncio.AbstractEventLoop', result_queue=None):
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
    loop.run_until_complete(main(Config.from_cli(), loop))
