import time
import hashlib
import requests
from urllib.parse import urljoin
from typing import Any, Mapping


class FoxESSException(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


class FoxESSClient:
    def __init__(self, token: str):
        self.token = token

    @staticmethod
    def _get_timestamp() -> int:
        return round(time.time() * 1000)

    @staticmethod
    def _get_signature(path: str, token: str, timestamp: int) -> str:
        return hashlib.md5(fr'{path}\r\n{token}\r\n{timestamp}'.encode('utf-8')).hexdigest()

    @staticmethod
    def _get_headers(path: str, token: str, timestamp: int) -> Mapping[str, str | bytes]:
        return {
            'token': token,
            'lang': 'en',
            'timestamp': str(timestamp),
            'signature': FoxESSClient._get_signature(path, token, timestamp),
        }

    def request(self, method: str, path: str, headers: Mapping[str, str | bytes] = {}, **kwargs) -> dict[str, Any]:
        timestamp = FoxESSClient._get_timestamp()
        headers = { **headers, **FoxESSClient._get_headers(path, self.token, timestamp)}

        response = requests.request(method, urljoin('https://www.foxesscloud.com/', path), headers=headers, **kwargs)

        if response.status_code != 200:
            raise FoxESSException(response.status_code, '')

        response = response.json()

        if response['errno'] != 0:
            raise FoxESSException(response['errno'], response['msg'])

        return response

    def get_remaining_requests(self) -> int:
        response = self.request('get', '/op/v0/user/getAccessCount')
        return int(response['result']['remaining'])

    def get_inverters(self) -> list[str]:
        response = self.request('post', '/op/v0/device/list', json={ 'currentPage': 1, 'pageSize': 10 })
        return [inverter['deviceSN'] for inverter in response['result']['data']]

