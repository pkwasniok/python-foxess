import os
import time
import json
import dotenv
from foxess import FoxESSClient, FoxESSInverter
from paho.mqtt.client import CallbackAPIVersion as MQTTCallbackAPIVersion, Client as MQTTClient

dotenv.load_dotenv()

foxess = FoxESSClient(os.getenv('FOXESS_TOKEN'))
inverter = FoxESSInverter(foxess, os.getenv('FOXESS_INVERTER'))
mqtt = MQTTClient(MQTTCallbackAPIVersion.VERSION2)

def main():
    mqtt.connect('mqtt.sourcloud.pl', 1883, 60)
    mqtt.on_connect = on_connect

    mqtt.loop_start()

    while True:
        power = inverter.get_power()
        mqtt.publish('foxess/power', power)

        time.sleep(10)

    mqtt.loop_stop()

def on_connect(client, *args):
    client.publish(f'homeassistant/device/{inverter.sn}/config', json.dumps({
        'device': {
            'identifiers': [inverter.sn],
            'name': f'FoxESS {inverter.model}',
            'manufacturer': 'FoxESS',
            'model': inverter.model,
            'sn': inverter.sn,
        },
        'origin': {
            'name': 'python_foxess',
        },
        'components': {
            'foxess_power': {
                'unique_id': 'foxess_power',
                'name': 'Power',
                'platform': 'sensor',
                'device_class': 'power',
                'unit_of_measurement': 'kW',
                'state_topic': 'foxess/power',
            },
        },
    }))

if __name__ == '__main__':
    main()

