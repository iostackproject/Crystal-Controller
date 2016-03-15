from abstract_metric import Metric
from metrics_parser import SwiftMetricsParse
import itertools
import json 
import redis
import requests

class Get_Disk_Stats(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum', \
            'stop_actor', 'join_disk_stats']
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

    def attach(self, observer, stats_obs):
        """
        Asyncronous method. This method allows to be called remotelly. It is called from
        observers in order to subscribe in this workload metric. This observer will be
        saved in a dictionary type structure where the key will be the tenant assigned in the observer,
        and the value will be the PyActive proxy to connect to the observer.

        :param observer: The PyActive proxy of the oberver rule that calls this method.
        :type observer: **any** PyActive Proxy type
        """
        if stats_obs:
            self.stats_observer = observer

    def notify(self, body):
        try:
            self.join_disk_stats(json.loads(body))
            self.stats_observer.update(self.name, self.node_stats)
        except:
            print "Not stats_observer"

    def join_disk_stats(self, disk_stats):
        for dev in disk_stats:
            self.node_stats[dev] = disk_stats[dev]


    def get_value(self):
        return self.value

    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)
