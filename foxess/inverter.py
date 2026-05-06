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
        """Model name.
        """

        assert 'deviceType' in self._details and isinstance(self._details['deviceType'], str)
        return self._details['deviceType']

    @property
    def version(self) -> str:
        """Software version.
        """

        assert 'masterVersion' in self._details and isinstance(self._details['masterVersion'], str)
        return self._details['masterVersion']

    def get_status(self) -> FoxESSInverterStatus:
        """Return current status of inverter.
        """

        self._refresh_details()
        assert 'status' in self._details and isinstance(self._details['status'], int)

        return FoxESSInverterStatus.from_code(self._details['status'])

    def get_power(self) -> float:
        """Return value of currently produced power in kW.
        """

        self._refresh_variables()
        assert 'pvPower' in self._variables and isinstance(self._variables['pvPower'], float)

        return self._variables['pvPower']

    def get_energy(self) -> float:
        """Return value of energy produced today in kWh.
        """

        self._refresh_variables()
        assert 'todayYield' in self._variables and isinstance(self._variables['todayYield'], float)

        return self._variables['todayYield']

    def get_grid_voltages(self) -> tuple[float, float, float]:
        """Return values of grid voltages in V.
        """

        self._refresh_variables()
        assert 'RVolt' in self._variables and isinstance(self._variables['RVolt'], float)
        assert 'SVolt' in self._variables and isinstance(self._variables['SVolt'], float)
        assert 'TVolt' in self._variables and isinstance(self._variables['TVolt'], float)

        return (self._variables['RVolt'], self._variables['SVolt'], self._variables['TVolt'])

    def get_grid_frequencies(self) -> tuple[float, float, float]:
        """Return frequencies of grid voltages in Hz.
        """

        self._refresh_variables()
        assert 'RFreq' in self._variables and isinstance(self._variables['RFreq'], float)
        assert 'SFreq' in self._variables and isinstance(self._variables['SFreq'], float)
        assert 'TFreq' in self._variables and isinstance(self._variables['TFreq'], float)

        return (self._variables['RFreq'], self._variables['SFreq'], self._variables['TFreq'])

