
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
from collections import OrderedDict
import requests
import operator
import json
import redis
import pika
import logging
import ConfigParser

mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne, "OR":operator.or_, "AND":operator.and_}

#TODO: Add the redis connection into rule object
logging.basicConfig(filename='./rule.log', format='%(asctime)s %(message)s', level=logging.INFO)


class Rule_Stats(object):
    """
    Rule: Each policy of each tenant is compiled as Rule. Rule is an Actor and it will be subscribed
    in the workloads metrics. When the data received from the workloads metrics satisfies
    the conditions defined in the policy,the Rule actor executes an Action that it is
    also defined in the policy.
    """
    _sync = {'get_tenant':'2'}
    _async = ['update', 'start_rule', 'stop_actor', 'add_metric']
    _ref = []
    _parallel = []

    def __init__(self, host, host_ip, host_port, host_transport):
        """
        Inicialize all the variables needed for the rule.

        :param host: The proxy host provided by the PyActive Middleware.
        :type host: **any** PyActive Proxy type
        :param host_ip: The host ip adress.
        :type host_ip: **any** String type
        :param host_port: The host port address.
        :type host_port: **any** Numeric type.
        :param host_transport: The host transport used for the comunication.
        :type host_transport: **any** String type.

        """
        settings = ConfigParser.ConfigParser()
        settings.read("./dynamic_policies.config")
        logging.info('Rule init: OK')
        self.base_uri = host_transport+'://'+host_ip+':'+str(host_port)+'/'
        self.host = host
        self.redis_host = settings.get('redis', 'host')
        self.redis_port = settings.get('redis', 'port')
        self.redis_db = settings.get('redis', 'db')
        self.sorting_method = "mean_bw"
        self.key = "sorted_nodes:" + self.sorting_method

        try:
            self.r = redis.Redis(connection_pool=redis.ConnectionPool(host=self.redis_host, port=self.redis_port, db=0))
        except:
            return Response('Error connecting with DB', status=500)

    def add_metric(self):
        """
        The `add_metric()` method subscribes the rule to all workload metrics that it
        needs to check the conditions defined in the policy

        :param workload_name: The name that identifies the workload metric.
        :type workload_name: **any** String type

        """
        try:
            observer = self.host.lookup(self.base_uri+'metrics.get_disk_stats/Get_Disk_Stats/get_disk_stats')
            observer.attach(self.proxy, True)
        except:
            raise Exception('Error attaching to metric get_disk_stats')

    def update(self, metric, info):
        self.update_redis(info)

        
    def sort(self, devices):
        return OrderedDict(sorted(devices.items(), key=lambda x: x[1]['mean-1min']))

    def update_redis(self, nodes):
        for n in nodes
            self.r.hset(self.key, n.replace("/mnt",""), nodes[n]['mean-1min'])

    def get_tenant(self):
        """
        Return the tenant assigned to this rule.

        :return: Return the tenant id assigned to this rule
        :rtype: String type.
        """
        return self.tenant
