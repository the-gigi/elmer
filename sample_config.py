import os

hosts = ['xxx.xxx.xxx.xxx', 'yyy.yyy.yyy.yyy', 'zzz.zzz.zzz.zzz']
disc_nodes  = (('host-1','xxx.xxx.xxx.xxx'), ('host-2','yyy.yyy.yyy.yyy'))
ram_nodes   = (('host-3','zzz.zzz.zzz.zzz'),)

user = 'user'
password = os.environ['RMQ_CLUSTER_PASSWORD']
admin_user = 'admin'
admin_password = os.environ['RMQ_ADMIN_PASSWORD']

# Real config
cluster_config = dict(
    vhost='awesome-vhost',
    users=[dict(name='awesome-reader', password='secret',
                configure='', read='.*', write='', tags=''),
           dict(name='awesome-writer', password='super-secret',
                configure='', read='', write='.*', tags='')],
    exchanges = [dict(name='awesome-exchange-1',
                      exchange_type='direct'),
                 dict(name='awesome-exchange-2',
                 exchange_type='fanout')],
    queues = [dict(node='',
                   exchange='awesome-exchange-1',
                   queue='ephemeral-queue',
                   auto_delete='false', durable='false'),
              dict(node='',
                   exchange='awesome-exchange-2',
                   queue='persistent-queue',
                   auto_delete='false', durable='true')])
