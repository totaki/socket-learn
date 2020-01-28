import json
from typing import Union
from argparse import ArgumentParser


Int = Union[str, int]


class Config:
    def __init__(self,
                 server_address: str,
                 server_port: Int,
                 service_address: str,
                 service_port: Int,
                 service_conn_count: Int,
                 service_max_delay: Int,
                 application_port: Int,
                 application_address: Int,
                 poll_wait: Int,
                 size_hint: Int,
                 client_max_delay: Int,
                 client_count: Int,
                 ):
        self.server_address = server_address
        self.server_port = server_port
        self.service_address = service_address
        self.service_port = service_port
        self.service_conn_count = service_conn_count
        self.service_max_delay = service_max_delay
        self.application_address = application_address
        self.application_port = application_port
        self.poll_wait = poll_wait
        self.size_hint = size_hint
        self.client_max_delay = client_max_delay
        self.client_count = client_count

    @classmethod
    def load(cls, file_name: str) -> 'Config':
        with open(file_name) as f:
            _config = json.load(f)
            print('\nLoad config:')
            for k in sorted(_config):
                print_key = ' '.join(k.split('_')).capitalize()
                print(f'    {print_key}: {_config[k]}')
            return cls(**_config)

    @classmethod
    def from_cli(cls):
        parser = ArgumentParser()
        parser.add_argument('--config', default='default_config.json', required=False)
        args = parser.parse_args()
        return cls.load(args.config)