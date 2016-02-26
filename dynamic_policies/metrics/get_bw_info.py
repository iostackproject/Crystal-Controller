from abstract_metric import Metric
from metrics_parser import SwiftMetricsParse
import json
import redis
import requests

class Get_Bw_Info(Metric):
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
        self.name = "get_bw_info"
        self.exchange = exchange
        self.parser_instance = SwiftMetricsParse()
        print 'Get_bw_info initialized'
        self.count = {}
        self.last_bw = {}

    def attach(self, observer, special=None):
        """
        Asyncronous method. This method allows to be called remotelly. It is called from
        observers in order to subscribe in this workload metric. This observer will be
        saved in a dictionary type structure where the key will be the tenant assigned in the observer,
        and the value will be the PyActive proxy to connect to the observer.

        :param observer: The PyActive proxy of the oberver rule that calls this method.
        :type observer: **any** PyActive Proxy type
        """
        if special:
            self.special_observer = observer
        else:
            tenant = observer.get_tenant()
            if not tenant in self._observers.keys():
                self._observers[tenant] = set()
            if not observer in self._observers[tenant]:
                self._observers[tenant].add(observer)

    def notify(self, body):
        self.parse_osinfo(json.loads(body))
        try:
            self.special_observer.update(self.name, self.count)
        except:
            return "Not special observer"

        for tentant, observer_set in self._observers.items():
            if tenant in self.count.keys():
                for observer in observer_set:
                    observer.update(self.name, self.count[tenant])

        print self.count



    def parse_osinfo(self, osinfo):
        for ip in osinfo:
            for account in self.count:
                self.count[account][ip] = {}
            for dev in osinfo[ip]:
                for th in osinfo[ip][dev]:
                    account = osinfo[ip][dev][th]["account"]
                    policy = osinfo[ip][dev][th]["policy"]
                    if not account in self.count:
                        self.count[account] = {}
                    if not ip in self.count[account]:
                        self.count[account][ip] = {}
                    for obj in osinfo[ip][dev][th]["objects"]:
                        if not policy in self.count[account][ip]:
                            self.count[account][ip][policy] = obj['oid_calculated_BW']
                        else:
                            self.count[account][ip][policy] += obj['oid_calculated_BW']

    def get_value(self):
        return self.value

    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)
