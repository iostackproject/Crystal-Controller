from abstract_metric import Metric
from metrics_parser import SwiftMetricsParse
import itertools
import json 
import redis
import requests

class Get_Disk_Stats(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum', \
            'stop_actor', 'get_redis_bw', 'compute_assignations', 'parse_osinfo', 'send_bw']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, exchange, queue, routing_key, host):
        Metric.__init__(self)

        self.host = host
        self.queue = queue
        self.routing_key = routing_key
        self.name = "get_disk_stats"
        self.exchange = exchange
        self.parser_instance = SwiftMetricsParse()
        print 'Get_Disk_stats initialized'
        self.node_stats = {}

    def notify(self, body):
        try:
            self.parse_disk_stats(json.loads(body))
            print self.node_stats
        except:
            pass

    def parse_disk_stats(self, disk_stats):
        for dev in disk_stats:
            self.node_stats[dev] = disk_stats[dev]


    def get_value(self):
        return self.value

    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)
