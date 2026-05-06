import time
from enum import Enum
from .client import FoxESSClient


class FoxESSInverterStatus(Enum):
    ONLINE = 1
    ERROR = 2
    OFFLINE = 3

    @staticmethod
    def from_code(code: int):
        match code:
            case 1:
                return FoxESSInverterStatus.ONLINE
            case 2:
                return FoxESSInverterStatus.ERROR
            case 3:
                return FoxESSInverterStatus.OFFLINE


class FoxESSInverter:
    def __init__(self, client: FoxESSClient, sn: str):
        self.client = client
        self.sn = sn

        self._variables: dict[str, int | float | str] = self._request_variables()
        self._details: dict[str, int | float | str] = self._request_details()

        self._timestamp_variables: float = time.time()
        self._timestamp_details: float = time.time()

    def _request_details(self) -> dict[str, int | float | str]:
        response = self.client.request('get', '/op/v0/device/detail', params={ 'sn': self.sn })
        return response['result']

    def _request_variables(self) -> dict[str, int | float | str]:
        response = self.client.request('post', '/op/v1/device/real/query', json={ 'sns': [self.sn] })

        variables = {}
        for variable in response['result'][0]['datas']:
            variables[variable['variable']] = variable['value']

        return variables

    def _refresh_variables(self) -> None:
        if time.time() - self._timestamp_variables <= 60:
            return

        self._variables = self._request_variables()

    def _refresh_details(self) -> None:
        if time.time() - self._timestamp_details <= 120:
            return

        self._details = self._request_details()

    @property
    def model(self) -> str:
        assert 'deviceType' in self._details and isinstance(self._details['deviceType'], str)
        return self._details['deviceType']

    @property
    def version(self) -> str:
        assert 'masterVersion' in self._details and isinstance(self._details['masterVersion'], str)
        return self._details['masterVersion']

    def get_status(self) -> FoxESSInverterStatus:
        self._refresh_details()
        assert 'status' in self._details and isinstance(self._details['status'], int)

        return FoxESSInverterStatus.from_code(self._details['status'])

    def get_power(self) -> float:
        self._refresh_variables()
        assert 'pvPower' in self._variables and isinstance(self._variables['pvPower'], float)

        return self._variables['pvPower']

