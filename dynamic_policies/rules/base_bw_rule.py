import redis
import pika
import logging
import ConfigParser

logging.basicConfig(filename='./rule.log', format='%(asctime)s %(message)s', level=logging.INFO)

class AbstractEnforcementAlgorithm(object):
    """
    TODO: Review the documentation of this class

    AbstractEnforcementAlgorithm:
    """
    _sync = {'get_tenant':'2'}
    _async = ['update', 'run']
    _ref = []
    _parallel = []

    def __init__(self, name, method):
        """
        """
        settings = ConfigParser.ConfigParser() 
        settings.read("./dynamic_policies.config")

        logging.info('Rule init: OK')
        self.rmq_user = settings.get('rabbitmq', 'username')
        self.rmq_pass = settings.get('rabbitmq', 'password')
        self.rmq_host = settings.get('rabbitmq', 'host')
        self.rmq_port = int(settings.get('rabbitmq', 'port'))
        self.rmq_exchange = "bw_assignations" #settings.get('rabbitmq', 'exchange')
        
        self.redis_host = settings.get('redis', 'host')
        self.redis_port = int(settings.get('redis', 'port'))
        self.redis_db = int(settings.get('redis', 'db'))
        
        self.credentials = pika.PlainCredentials(self.rmq_user, self.rmq_pass)
        
        try:
            self.r = redis.Redis(connection_pool=redis.ConnectionPool(host=self.redis_host, 
                                                                      port=self.redis_port, 
                                                                      db=self.redis_db))
        except:
            logging.info('"Error connecting with Redis DB"')
            print "Error connecting with Redis DB"
            
        self.last_bw = dict()
        self.name = name
        self.method = method

    def run(self, workload_metic_id):
        """
        The `run()` method subscribes the rule to all workload metrics that it
        needs to check the conditions defined in the policy

        :param workload_name: The name that identifies the workload metric.
        :type workload_name: **any** String type

        """
        try:
            observer = self.host.lookup(workload_metic_id)
            observer.attach(self.proxy, True)
        except Exception as e:
            raise Exception('Error attaching to metric bw_info: '+str(e))

    def connect_rmq(self):
        #TODO: WARNING: BlockingConnection can block the actor
        self._connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=self.redis_host, credentials=self.credentials))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange=self.rmq_exchange, exchange_type='topic')

    def disconnect_rmq(self):
        self._channel.close()
        self._connection.close()

    def send_message_rmq(self, message, routing_key):
        self.connect_rmq()
        self._channel.basic_publish(exchange=self.rmq_exchange,routing_key=routing_key, body=str(message))
        #self.disconnect_rmq()

    def update(self, metric, info):
        results = self.compute_algorithm(info)
        self.send_results(results)
        self.last_bw = results

    def compute_algorithm(self, info):
        """
        return exception unnimplemented method
        """
        return NotImplemented

    def _get_redis_bw(self):
        """
        Gets the bw assignation from the redis database
        """
        bw = dict()
        keys = self.r.keys("bw:*")
        for key in keys:
            bw[key[3:]] = self.r.hgetall(key)
        return bw

    def send_results(self, assign):
        """
        Sends the calculated BW to each Node that has active requests
        """
        for account in assign:
            for ip in assign[account]:		
                new_flow = account not in self.last_bw or ip not in self.last_bw[account]
                if not new_flow and int(assign[account][ip]) == int(self.last_bw[account][ip]):
                    break
                node_ip = ip.split('-')
                address = node_ip[0]+'/'+account+'/'+self.method+'/'+ node_ip[1]+'/'+node_ip[2]+'/'+str(round(assign[account][ip],1))
                routing_key = '.'+node_ip[0].replace('.','-').replace(':','-') + "."
                print "BW CHANGED: "+ str(address)
                self.send_message_rmq(address, routing_key)

    def get_tenant(self):
        """
        Return the tenant assigned to this rule.

        :return: Return the tenant id assigned to this rule
        :rtype: String type.
        """
        return self.tenant
