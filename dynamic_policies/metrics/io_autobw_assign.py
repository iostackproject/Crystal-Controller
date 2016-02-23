from abstract_metric import Metric
from metrics_parser import SwiftMetricsParse
import json 
import redis
import requests

class IO_Autobw_Assign(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum', 'stop_actor', 'get_redis_bw', \
            'compute_assignations', 'parse_osinfo']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, exchange, queue, routing_key, host):
        Metric.__init__(self)

        self.host = host
        self.queue = queue
        self.routing_key = routing_key
        self.name = "io_autobw_assign"
        self.exchange = exchange
        self.parser_instance = SwiftMetricsParse()
        print 'IO_autobw_assign initialized'
        self.count = {}
        self.last_bw = {}

    def notify(self, body):
        self.parse_osinfo(json.loads(body))
        self.assignations = self.compute_assignations()
        
        for account in self.assignations:
            for policy in self.assignations[account]:
                try:
                    if self.assignations[account][policy]['bw'] != \
                                self.last_bw[account][policy]['bw']:
                            for ip in self.assignations[account][policy]['ips']:
                                address = "http://" + ip + "/bwmod/" + account + "/" \
                                + policy + "/" + str(self.assignations[account][policy]['bw']) + "/"
                                r = requests.get(address)
                except:
                    for ip in self.assignations[account][policy]['ips']:
                        address = "http://" + ip + "/bwmod/" + account + "/" \
                        + policy + "/" + str(self.assignations[account][policy]['bw']) + "/"
                        r = requests.get(address)
        self.last_bw = self.assignations

    def get_redis_bw(self):
        """
        Gets the bw assignation from the redis database
        """
        bw = dict()
        try:
            r = redis.Redis(connection_pool=redis.ConnectionPool(host=self.redis_host, port=self.redis_port, db=0))
        except:
            return Response('Error connecting with DB', status=500)
        keys = r.keys("bw:*")
        for key in keys:
            bw[key[3:]] = r.hgetall(key)
        return bw

    def compute_assignations(self):
        assign = dict()
        bw = self.get_redis_bw()
        for account in self.count:
            assign[account] = dict()
            for ip in self.count[account]:
                for policy in self.count[account][ip]:
                    if not policy in assign[account]:
                        assign[account][policy] = dict()
                    if not 'num' in assign[account][policy]:
                        assign[account][policy]['num'] = 1
                    else:
                        assign[account][policy]['num'] += 1
                    assign[account][policy]['bw'] = int(bw[account][policy])/assign[account][policy]['num']
                    if not 'ips' in assign[account][policy]:
                        assign[account][policy]['ips'] = []
                    assign[account][policy]['ips'].append(ip)

        return assign

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
                    self.count[account][ip] = {}
                    for obj in osinfo[ip][dev][th]["objects"]:
                        if not policy in self.count[account][ip]:
                            self.count[account][ip][policy] = 1
                        else: 
                            self.count[account][ip][policy] += 1

    def get_value(self):
        return self.value

    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)
