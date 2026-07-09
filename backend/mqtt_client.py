"""
mqtt_client.py - Subscribes to all drone telemetry topics.

Runs paho-mqtt in a background thread. When a message arrives it:
  1. Updates the in-memory position store.
  2. Pushes the payload onto the asyncio queue so the broadcaster
     coroutine can fan it out to WebSocket clients.

Thread-safety note:
  paho callbacks run on the paho network thread.
  asyncio.Queue.put_nowait is scheduled via loop.call_soon_threadsafe
  so it is safe to call from any thread.
"""

import asyncio
import json
import logging
import os

import paho.mqtt.client as mqtt

from .store import store

log = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
TOPIC       = "drone/+/telemetry"


def start_mqtt(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> mqtt.Client:
    """
    Initialise and start the paho MQTT client in its own network thread.
    Returns the client so the caller can stop it on shutdown.
    """

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(TOPIC, qos=0)
            log.info(f"MQTT subscribed → {TOPIC}")
        else:
            log.error(f"MQTT connect failed: reason_code={reason_code}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        drone_id = payload.get("drone_id")
        if not drone_id:
            return

        # 1. Update the thread-safe store immediately
        store.update(drone_id, payload)

        # 2. Schedule a put onto the asyncio queue from this paho thread
        loop.call_soon_threadsafe(queue.put_nowait, payload)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
        log.info(f"MQTT client started → {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        log.error(
            f"MQTT connection failed: {e}\n"
            "Make sure Mosquitto is running: net start mosquitto"
        )

    return client
