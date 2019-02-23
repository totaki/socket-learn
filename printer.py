import time


def print_state(str_name, *str_args):
    print('{:.8f}, {:>16}, {}'.format(
        time.time(),
        str_name,
        ', '.join(['{:>16}'.format(str_item) for str_item in str_args])
    ))
