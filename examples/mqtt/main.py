import os
import time
import json
import dotenv
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

sensors = [
    {
        'name': 'power',
        'label': 'Power',
        'class': 'power',
        'unit': 'kW',
        'get': lambda: inverter.get_power(),
    },
    {
        'name': 'energy',
        'label': 'Energy',
        'class': 'energy',
        'unit': 'kWh',
        'get': lambda: inverter.get_energy(),
    },
    {
        'name': 'voltage_l1',
        'label': 'Voltage L1',
        'class': 'voltage',
        'unit': 'V',
        'get': lambda: inverter.get_grid_voltages()[0],
    },
    {
        'name': 'voltage_l2',
        'label': 'Voltage L2',
        'class': 'voltage',
        'unit': 'V',
        'get': lambda: inverter.get_grid_voltages()[1],
    },
    {
        'name': 'voltage_l3',
        'label': 'Voltage L3',
        'class': 'voltage',
        'unit': 'V',
        'get': lambda: inverter.get_grid_voltages()[2],
    },
    {
        'name': 'frequency_l1',
        'label': 'Frequency L1',
        'class': 'frequency',
        'unit': 'Hz',
        'get': lambda: inverter.get_grid_frequencies()[0],
    },
    {
        'name': 'frequency_l2',
        'label': 'Frequency L2',
        'class': 'frequency',
        'unit': 'Hz',
        'get': lambda: inverter.get_grid_frequencies()[1],
    },
    {
        'name': 'frequency_l3',
        'label': 'Frequency L3',
        'class': 'frequency',
        'unit': 'Hz',
        'get': lambda: inverter.get_grid_frequencies()[2],
    },
]

def main():
    mqtt.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt.on_connect = on_connect

    mqtt.loop_start()

    time_status = 0
    time_data = 0
    status = inverter.get_status()

    while True:
        if time.time() - time_status >= 10 * 60:
            status = inverter.get_status()
            match status:
                case FoxESSInverterStatus.ONLINE:
                    mqtt.publish(f'foxess/{inverter.sn}/status', 'online')
                case FoxESSInverterStatus.ERROR:
                    mqtt.publish(f'foxess/{inverter.sn}/status', 'online')
                case FoxESSInverterStatus.OFFLINE:
                    mqtt.publish(f'foxess/{inverter.sn}/status', 'offline')
        if (status == FoxESSInverterStatus.ONLINE or status == FoxeSSInverterStatus.ERROR) and time.time() - time_data >= 5 * 10:
            for sensor in sensors:
                mqtt.publish(f'foxess/{inverter.sn}/{sensor['name']}', sensor['get']())

        time.sleep(60)

    mqtt.loop_stop()

def on_connect(client, *args):
    components = {}
    for sensor in sensors:
        components[sensor['name']] = {
            'unique_id': f'{inverter.sn}_{sensor['name']}',
            'name': sensor['label'],
            'platform': 'sensor',
            'device_class': sensor['class'],
            'unit_of_measurement': sensor['unit'],
            'state_topic': f'foxess/{inverter.sn}/{sensor['name']}',
        }

    client.publish(f'homeassistant/device/{inverter.sn}/config', json.dumps({
        'device': {
            'identifiers': [inverter.sn],
            'name': f'FoxESS {inverter.model}',
            'manufacturer': 'FoxESS',
            'model': inverter.model,
            'serial_number': inverter.sn,
            'sw_version': inverter.version,
        },
        'origin': {
            'name': 'python_foxess',
        },
        'components': components,
    }), retain=True)

if __name__ == '__main__':
    main()

