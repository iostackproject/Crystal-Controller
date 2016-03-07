
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
import requests
import operator
import json
import redis
import pika
import logging

mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne, "OR":operator.or_, "AND":operator.and_}

#TODO: Add the redis connection into rule object
r = redis.StrictRedis(host='localhost', port=6379, db=0)
logging.basicConfig(filename='./rule.log', format='%(asctime)s %(message)s', level=logging.INFO)


class Rule_Bw(object):
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

        :param rule_parsed: The rule parsed by the dsl_parser.
        :type rule_parsed: **any** PyParsing type
        :param tenant: The tenant id assigned to this rule.
        :type tenant_info: **any** String type
        :param host: The proxy host provided by the PyActive Middleware.
        :type host: **any** PyActive Proxy type
        :param host_ip: The host ip adress.
        :type host_ip: **any** String type
        :param host_port: The host port address.
        :type host_port: **any** Numeric type.
        :param host_transport: The host transport used for the comunication.
        :type host_transport: **any** String type.

        """
        logging.info('Rule init: OK')
        self.base_uri = host_transport+'://'+host_ip+':'+str(host_port)+'/'
        self.host = host
        self.redis_host='84.88.51.222'
        self.redis_port=6379
        self.rmq_user =  'guest'
        self.rmq_pass = 'guest'
        self.rmq_host = '84.88.51.222'
        self.rmq_port = 5672
        self.rmq_exchange = 'bw_assignations'
        credentials = pika.PlainCredentials(self.rmq_user, self.rmq_pass)
        self._channel = pika.BlockingConnection(pika.ConnectionParameters(
            host=self.redis_host, credentials=credentials)).channel()
        self._channel.exchange_declare(exchange=self.rmq_exchange,
                         exchange_type='topic')

        self.last_bw={}

    def add_metric(self):
        """
        The `add_metric()` method subscribes the rule to all workload metrics that it
        needs to check the conditions defined in the policy

        :param workload_name: The name that identifies the workload metric.
        :type workload_name: **any** String type

        """
        try:
            observer = self.host.lookup(self.base_uri+'metrics.get_bw_info/Get_Bw_Info/get_bw_info')
            observer.attach(self.proxy, True)
        except:
            raise Exception('Error attaching to metric get_bw_info')


    def update(self, metric, info):
        self.assignations = self.compute_assignations(info)
        self.send_bw()

    def compute_assignations(self, info):
        """
        Algoritme d'assignació de BW
        """
        assign = dict()
        bw = self.get_redis_bw()
        for account in info:
            assign[account] = dict()
            for ip in info[account]:
                for policy in info[account][ip]:
                    if not policy in assign[account]:
                        assign[account][policy] = dict()
                    if not 'num' in assign[account][policy]:
                        assign[account][policy]['num'] = 1
                        assign[account][policy]['real_bw'] = info[account][ip][policy]
                    else:
                        assign[account][policy]['num'] += 1
                        assign[account][policy]['real_bw'] += info[account][ip][policy]
                    assign[account][policy]['bw'] = int(bw[account][policy])/assign[account][policy]['num']
                    if not 'ips' in assign[account][policy]:
                        assign[account][policy]['ips'] = []
                    assign[account][policy]['ips'].append(ip)
        return assign


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

    def send_bw(self):
        routing_key = "."
        address = " "
        send = False
        for account in self.assignations:
            for policy in self.assignations[account]:
                if account in self.last_bw and policy in self.last_bw[account]:
                    if self.assignations[account][policy]['bw'] != self.last_bw[account][policy]['bw']:
                        print "BW CHANGED"
                        send = True
                        address = address +'/'+account+'/'+policy+'/'+str(self.assignations[account][policy]['bw'])+'/ '
                        for ip in self.assignations[account][policy]['ips']:
                            routing_key = routing_key + ip.replace('.','-').replace(':','-') + "."
                else:
                    print "BW CHANGED"
                    send = True
                    address = address + "/" + account + "/" + policy + "/" + str(self.assignations[account][policy]['bw']) + "/ "
                    for ip in self.assignations[account][policy]['ips']:
                        routing_key = routing_key + ip.replace('.','-').replace(':','-') + "."
        if send:
            self._channel.basic_publish(exchange='bw_assignations',routing_key=routing_key, body=str(address))
            print routing_key
            print address
            self.last_bw = self.assignations

    def get_tenant(self):
        """
        Retrun the tenant assigned to this rule.

        :return: Return the tenant id assigned to this rule
        :rtype: String type.
        """
        return self.tenant
