import os
import sys
import copy
import time
import datetime
import fabric
from fabric.api import (sudo,
                        env,
                        task,
                        hosts,
                        settings,
                        hide,
                        show)
from fabric.tasks import execute

import config

"""A Fabric file to control a RabbitMQ cluster

The cluster hosts, user and password are defined in config.py

You can start and stop the service on remote hosts
You can execute any rabbitmqctl command using the rmq method

Finally you can create a whole cluster from scratch and administer it.

The script assumes the following:

- The cluster nodes run the same versions of Erlang and RabbitMQ
- The cluster nodes run on *nix OS
- The Erlang cookie is identical on all hosts (verify with show_cookies task)
- RabbitMQ is installed in the default location using the default configuration
- Python 2.6+ is installed in /usr/local/bin/python
- The RabbitMQ command-line admin is installed in /usr/local/bin/rabbitmqadmin
- All nodes are called rabbit@<host>
- All nodes have a user with sudo priviliges and the same credentials
"""

# Keep going if a command fails on some host
env.skip_bad_hosts = True
env.warn_only = True

# Set the hosts to all hosts from the configuration, if not specified
if env.hosts == []:
    env.hosts = config.hosts

# Cluster Credentials (same across all machines)
env.user = config.user
env.password = config.password

@task
def start_server():
    """Start a server remotely

    The nohup at the beginning is critical, otherwise
    the remote shell will cause the server to hang up when it exits
    immediately after lanching the server.
    """
    return sudo('nohup /sbin/service rabbitmq-server start')


def wait_for_server(node):
    """Start the server (if not running already)

    Return True if the server managed to start in 5 seconds and False otherwise
    """
    if is_rabbit_running(node):
        return True

    # Really stop it, in case it's in stop_app state
    rmq('stop')

    # now start from scratch
    s = start_server()
    end = datetime.datetime.now() + datetime.timedelta(seconds=5)
    while (not is_rabbit_running(node) and datetime.datetime.now() < end):
        time.sleep(0.1)

    return is_rabbit_running(node)

@task
def rmq(command):
    """The main interface to control the cluster (wraps rabbitmqctl)

    The start command is forwarded to the start_server() function.
    All other commands are sent directly to rabbitmqctl
    """
    if command == 'start':
        return start_server()
    else:
        return sudo('/usr/sbin/rabbitmqctl ' + command)

#@hosts(*env.hosts)
@task
def show_cookies():
    return sudo('cat /var/lib/rabbitmq/.erlang.cookie')

def is_rabbit_running(host):
    """Check the status of RabbitMQ on the target node

    If the 'rabbit' and 'mensia' strings show up in the output
    of rmq('status') it means the rabbit is up and running
    """
    with settings(host_string=host):
        s = rmq('status')
        return '{rabbit,' in s and '{mnesia' in s

def build_cluster(disc_nodes, ram_nodes):
    """Reset all the nodes and build the cluster from scratch

    This script works regardless of which node was the last disc node
    and in what state each node is (up, down, stopped, etc)

    Must use force_reset when tearing down the cluste to aovid
    problems with the last disk node.
    """

    # Make Fabric less verbose
    #fabric.state.output['output'] = False
    with show('output'):
        nodes = disc_nodes + ram_nodes
        first = nodes[0][1]

        # Start all nodes. Keep nodes that failed to start (that's ok on first round)
        failed_to_start = []
        for host, node in nodes:
            with settings(host_string=node):
                ok = wait_for_server(node)
                if not ok:
                    failed_to_start.append((host, node))

        # Ohh, that's bad. Can't start even one. Nothing to do here. Bail out.
        if nodes == failed_to_start:
            print 'ERROR: Unable to start any node'
            return False

        # Start failed nodes again (the last disc node should be up now)
        for host, node in copy.copy(failed_to_start):
            with settings(host_string=node):
                ok = wait_for_server(node)
                if ok:
                    failed_to_start.remove((host, node))

        # Ohh, that's bad. Can't start some nodes on the second try. Bail out.
        if failed_to_start != []:
            print 'ERROR: Unable to start the following nodes:', failed_to_start
            return False

        # Reset all nodes
        for host, node in nodes:
            with settings(host_string=node):
                rmq('stop_app')
                rmq('force_reset')

        # Start only the first disc node
        with settings(host_string=first):
            r = rmq('start_app')

        print 'Waiting for ', first, 'to start_app...'
        while (not is_rabbit_running(first)):
            time.sleep(0.1)

    # Cluster all other nodes to the first node
    disc_node_names = ' '.join(('rabbit@' + host) for host, node in disc_nodes)

    for host, node in nodes[1:]:
        with settings(host_string=node):
            cluster_cmd = 'cluster ' + disc_node_names
            rmq(cluster_cmd)
            rmq('start_app')

            # Make sure the current node is really running as part of the cluster
            s = rmq('cluster_status')
            lines = s.split('\r\n')
            for line in lines:
                if 'running_nodes' in line:
                    if not 'rabbit@' + host in line:
                        return False
                    break

    return True

@task
def rmqa(command):
    """ """
    cmd = '/usr/local/bin/python /usr/local/bin/rabbitmqadmin -u %s -p %s %s'

    return sudo(cmd % (config.admin_user, config.admin_password, command))


    #'exchange':   {'mandatory': ['name', 'type'],
    #               'optional':  {'auto_delete': 'false', 'durable': 'true',
    #                             'internal': 'false'}},
    #'queue':      {'mandatory': ['name'],
    #               'optional':  {'auto_delete': 'false', 'durable': 'true',
    #                             'node': None}},
    #'binding':    {'mandatory': ['source', 'destination_type', 'destination',
    #                             'routing_key'],
    #               'optional':  {}},
    #'vhost':      {'mandatory': ['name'],
    #               'optional':  {}},
    #'user':       {'mandatory': ['name', 'password', 'tags'],
    #               'optional':  {}},
    #'permission': {'mandatory': ['vhost', 'user', 'configure', 'write', 'read'],
    #               'optional':  {}}

@task
def declare_exchange(vhost, name, exchange_type='direct'):
    """Declare an exchange on a particular virtual host

    The exchange_type may be 'direct', 'fanout', 'topic' or 'headers'
    """
    cmd ='declare exchange -V {0} name={1} type={2}'.format(vhost, name, exchange_type)
    rmqa(cmd)

@task
def declare_queue(vhost, node, name, auto_delete='false', durable='false'):
    """ """
    cmd ='declare queue -V {0} node={1} name={2} auto_delete={3}  durable={4}'
    cmd = cmd.format(vhost, node if node else 'rabbit', name, auto_delete, durable)
    rmqa(cmd)

@task
def bind(vhost, source, destination_type, destination, routing_key):
    """ """
    cmd ='declare binding -V {0} source={1} destination_type={2} destination={3} routing_key={4}'
    cmd = cmd.format(vhost, source, destination_type, destination, routing_key)
    rmqa(cmd)

@task
def declare_vhost(name):
    """ """
    cmd ='declare vhost name=' + name
    rmqa(cmd)

@task
def declare_permission(vhost, user, configure='.*', read='.*', write='.*'):
    cmd ='declare permission vhost={0} user={1} configure={2} read={3} write={4}'
    cmd =cmd.format(vhost, user, configure, read, write)
    rmqa(cmd)

@task
def add_user(vhost, username, password, configure='', read='', write='', tags=''):
    """Add a user + permissions to a vhost"""
    # Declare user
    cmd ='declare user -V {0} name={1} password={2} tags={3}'.format(vhost, username, password, tags)
    rmqa(cmd)

    # Declare permissions
    declare_permission(vhost, username, configure, read, write)


@task
def add_queue(vhost, node, exchange, queue, auto_delete='false', durable='false'):
    declare_queue(vhost, node, queue, auto_delete, durable)
    bind(vhost, exchange, 'queue', queue, '')

def admin_cluster(node, cluster_config, use_guest=False):
    """Setup the cluster with users, vhosts, exchanges and queues

    if use_guest is True it overrides the config's admin credentials and uses
    guest/guest instead (needed for the first time when the admin user was not
    created yet. duh).

    Once the admin user has been created you delete the guest account for
    security and call admin_cluster() without specifying use_guest=True.
    """

    admin_user = config.admin_user
    admin_password = config.admin_password

    if use_guest:
        config.admin_user = 'guest'
        config.admin_password = 'guest'

    with settings(host_string=node):
        vhost = cluster_config['vhost']
        declare_vhost(vhost)

        # Add the regular users
        for u in cluster_config['users']:
            add_user(vhost, u['name'], u['password'], u['configure'], u['read'], u['write'], u['tags'])

        # Add the admin user if currently using guest and restore admin user
        if use_guest:
            add_user(vhost, admin_user, admin_password, '.*', '.*', '.*', 'Administrator')
            config.admin_user = admin_user
            config.admin_password = admin_password

        # Declare the exchanges and queues using the admin user
        for e in cluster_config['exchanges']:
            declare_exchange(vhost, e['name'], e['exchange_type'])

        for q in cluster_config['queues']:
            add_queue(vhost, q.get('node', None),
                      q['exchange'], q['queue'], q['auto_delete'], q['durable'])

        # TODO: Delete guest user

def main():
    # Build the cluster from scratch
    ok = build_cluster(config.disc_nodes, config.ram_nodes)
    if not ok:
        print 'Oh no, failed to build the cluster :-('
        sys.exit(1)

    # Admin the cluster
    ok = admin_cluster(config.hosts[0], config.cluster_config, use_guest=True)
    if not ok:
        print 'Oh no, failed to administer the cluster :-('
        sys.exit(1)

if __name__ == '__main__':
    main()
    print 'Done.'