import json
import logging
import threading
import os

import socketio
from flask import Flask

from coinrat.candle_storage_plugins import CandleStoragePlugins
from coinrat.domain import DateTimeFactory
from coinrat.domain import Pair
from coinrat.order_storage_plugins import OrderStoragePlugins
from coinrat.server.event_types import EVENT_PING_REQUEST, EVENT_PING_RESPONSE, EVENT_GET_CANDLES, EVENT_GET_ORDERS, \
    EVENT_RUN_REPLY, EVENT_SUBSCRIBE, EVENT_UNSUBSCRIBE, EVENT_NEW_CANDLES, EVENT_NEW_ORDERS, EVENT_CLEAR_ORDERS
from coinrat.task.task_planner import TaskPlanner
from coinrat.domain.order import Order
from .order import serialize_orders, serialize_order
from .interval import parse_interval
from .candle import serialize_candles, MinuteCandle, serialize_candle


class SocketServer(threading.Thread):
    def __init__(
        self,
        task_planner: TaskPlanner,
        datetime_factory: DateTimeFactory,
        candle_storage_plugins: CandleStoragePlugins,
        order_storage_plugins: OrderStoragePlugins
    ):
        super().__init__()
        self.task_planner = task_planner
        socket = socketio.Server(async_mode='threading')

        @socket.on('connect')
        def connect(sid, environ):
            logging.info('Socket %s connected ', sid)

        @socket.on(EVENT_PING_REQUEST)
        def ping_request(sid, data):
            logging.info('RECEIVED: {}, {}'.format(EVENT_PING_REQUEST, data))

            data['response_timestamp'] = datetime_factory.now().timestamp()
            socket.emit(EVENT_PING_RESPONSE, data)

        @socket.on(EVENT_GET_CANDLES)
        def candles(sid, data):
            logging.info('RECEIVED: {}, {}'.format(EVENT_GET_CANDLES, data))

            if 'candle_storage' not in data:
                return 'ERROR', {'message': 'Missing "candle_storage" field in request.'}

            candle_storage = candle_storage_plugins.get_candle_storage(data['candle_storage'])
            result_candles = candle_storage.find_by(
                data['market'],
                Pair.from_string(data['pair']),
                parse_interval(data['interval'])
            )

            return 'OK', serialize_candles(result_candles)

        @socket.on(EVENT_GET_ORDERS)
        def orders(sid, data):
            logging.info('RECEIVED: {}, {}'.format(EVENT_GET_ORDERS, data))

            if 'order_storage' not in data:
                return 'ERROR', {'message': 'Missing "order_storage" field in request.'}

            order_storage = order_storage_plugins.get_order_storage(data['order_storage'])
            result_orders = order_storage.find_by(
                data['market'],
                Pair.from_string(data['pair']),
                interval=parse_interval(data['interval'])
            )

            return 'OK', serialize_orders(result_orders)

        @socket.on(EVENT_CLEAR_ORDERS)
        def clear_orders(sid, data):
            logging.info('RECEIVED: {}, {}'.format(EVENT_CLEAR_ORDERS, data))

            if 'order_storage' not in data:
                return 'ERROR', {'message': 'Missing "order_storage" field in request.'}

            order_storage = order_storage_plugins.get_order_storage(data['order_storage'])
            order_storage.delete_by(
                data['market'],
                Pair.from_string(data['pair']),
                interval=parse_interval(data['interval'])
            )

            return 'OK'

        @socket.on(EVENT_RUN_REPLY)
        def reply(sid, data):
            logging.info('Received Strategy REPLAY request: ' + json.dumps(data))
            self.task_planner.plan_replay_strategy(data)

            return 'OK'

        @socket.on('disconnect')
        def disconnect(sid):
            logging.info('Socket %s disconnect ', sid)

        self._socket = socket

    def emit_new_candle(self, candle: MinuteCandle):
        data = serialize_candle(candle)
        logging.info('EMITTING: {}, {}'.format(EVENT_NEW_CANDLES, data))
        self._socket.emit(EVENT_NEW_CANDLES, data)

    def emit_new_order(self, order: Order):
        data = serialize_order(order)
        logging.info('EMITTING: {}, {}'.format(EVENT_NEW_ORDERS, data))
        self._socket.emit(EVENT_NEW_ORDERS, data)

    def run(self):
        app = Flask(__name__)
        app.wsgi_app = socketio.Middleware(self._socket, app.wsgi_app)
        app.run(
            threaded=True,
            host=os.environ.get('SOCKET_SERVER_HOST'),
            port=int(os.environ.get('SOCKET_SERVER_PORT'))
        )

    def register_subscribes(self, on_subscribe: callable, on_unsubscribe: callable):
        self._socket.on(EVENT_SUBSCRIBE, on_subscribe)
        self._socket.on(EVENT_UNSUBSCRIBE, on_unsubscribe)