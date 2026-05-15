import os
import time
import json
import dotenv
from collections.abc import Callable
from dataclasses import dataclass
from foxess import FoxESSClient, FoxESSInverter, FoxESSInverterStatus
from paho.mqtt.client import CallbackAPIVersion as MQTTCallbackAPIVersion, Client as MQTTClient

dotenv.load_dotenv()

FOXESS_TOKEN = os.getenv('FOXESS_TOKEN')
FOXESS_INVERTER = os.getenv('FOXESS_INVERTER')
MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = os.getenv('MQTT_PORT', 1883)

foxess = FoxESSClient(FOXESS_TOKEN)
inverter = FoxESSInverter(foxess, FOXESS_INVERTER)
mqtt = MQTTClient(MQTTCallbackAPIVersion.VERSION2)


@dataclass
class MQTTSensor:
    name: str
    label: str
    unit: str | None
    device_class: str | None
    state_class: str | None
    get: Callable[[], str]
    availability: bool = False


@dataclass
class MQTTDevice:
    name: str
    label: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    sensors: list[MQTTSensor]


device = MQTTDevice(
    name = inverter.sn,
    label = f'FoxESS {inverter.model}',
    manufacturer = 'FoxESS',
    model = inverter.model,
    serial_number = inverter.sn,
    sensors = [
        MQTTSensor(
            name = 'status',
            label = 'Status',
            unit = None,
            device_class = 'enum',
            state_class = None,
            get = lambda: str(inverter.get_status()),
        ),
        MQTTSensor(
            name = 'power',
            label = 'Power',
            unit = 'kW',
            device_class = 'power',
            state_class = 'measurement',
            get = lambda: str(inverter.get_power()),
        ),
        MQTTSensor(
            name = 'energy_today',
            label = 'Energy (today)',
            unit = 'kWh',
            device_class = 'energy',
            state_class = 'total_increasing',
            get = lambda: str(inverter.get_energy()),
        ),
        MQTTSensor(
            name = 'voltage_l1',
            label = 'Voltage L1',
            unit = 'V',
            device_class = 'voltage',
            state_class = 'measurement',
            get = lambda: str(inverter.get_grid_voltages()[0]),
            availability = True,
        ),
        MQTTSensor(
            name = 'voltage_l2',
            label = 'Voltage L2',
            unit = 'V',
            device_class = 'voltage',
            state_class = 'measurement',
            get = lambda: str(inverter.get_grid_voltages()[1]),
            availability = True,
        ),
        MQTTSensor(
            name = 'voltage_l3',
            label = 'Voltage L3',
            unit = 'V',
            device_class = 'voltage',
            state_class = 'measurement',
            get = lambda: str(inverter.get_grid_voltages()[2]),
            availability = True,
        ),
        MQTTSensor(
            name = 'frequency_l1',
            label = 'Frequency L1',
            unit = 'Hz',
            device_class = 'frequency',
            state_class = 'measurement',
            get = lambda: str(inverter.get_grid_frequencies()[0]),
            availability = True,
        ),
        MQTTSensor(
            name = 'frequency_l2',
            label = 'Frequency L2',
            unit = 'Hz',
            device_class = 'frequency',
            state_class = 'measurement',
            get = lambda: str(inverter.get_grid_frequencies()[1]),
            availability = True,
        ),
        MQTTSensor(
            name = 'frequency_l3',
            label = 'Frequency L3',
            unit = 'Hz',
            device_class = 'frequency',
            state_class = 'measurement',
            get = lambda: str(inverter.get_grid_frequencies()[2]),
            availability = True,
        ),
    ],
)

def build_mqtt_discovery_payload(device: MQTTDevice):
    components = {}
    for sensor in device.sensors:
        components[sensor.name] = {
            'unique_id': f'{device.name}_{sensor.name}',
            'name': sensor.label,
            'platform': 'sensor',
            'device_class': sensor.device_class,
            'state_class': sensor.state_class,
            'unit_of_measurement': sensor.unit,
            'state_topic': f'foxess/{device.name}/{sensor.name}',
        }

        if sensor.availability == True:
            components[sensor.name]['availability_topic'] = f'foxess/{device.name}/status'

    return {
        'device': {
            'identifiers': device.name,
            'name': device.label,
            'manufacturer': device.manufacturer,
            'model': device.model,
            'serial_number': device.serial_number,
        },
        'origin': {
            'name': 'python-foxess',
        },
        'components': components,
    }

def main():
    mqtt.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt.on_connect = on_connect

    mqtt.loop_start()

    time.sleep(5)

    time_status = 0
    time_data = 0
    status = inverter.get_status()

    while True:
        if time.time() - time_status >= 15 * 60:
            time_status = time.time()

            status = inverter.get_status()
            mqtt.publish(f'foxess/{inverter.sn}/status', str(status))

        if time.time() - time_data >= 5 * 60 and (status in [FoxESSInverterStatus.ONLINE, FoxESSInverterStatus.ERROR]):
            time_data = time.time()

            for sensor in device.sensors:
                mqtt.publish(f'foxess/{device.name}/{sensor.name}', sensor.get())

        time.sleep(60)

    mqtt.loop_stop()

def on_connect(client, *args):
    client.publish(f'homeassistant/device/{inverter.sn}/config', json.dumps(build_mqtt_discovery_payload(device)), retain=True)

if __name__ == '__main__':
    main()

