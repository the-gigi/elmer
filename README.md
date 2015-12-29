Elmer
=====
A Fabric file called rabbit.py to control a [RabbitMQ](https://www.rabbitmq.com)
3.X cluster

The cluster hosts, user and password are defined in config.py. Copy the 
sample_config.py file and populate with your cluster's information.

You can start and stop the service on remote hosts
You can execute any rabbitmqctl command using the rmq() method

Finally you can create a whole cluster from scratch and administer it.

The script assumes the following:

- The cluster nodes are *nix boxes
- RabbitMQ 3.X is installed in the default location using the default 
configuration
- The node is called rabbit@<host>
- All the nodes can see each other (verify with ping)
- The Erlang cookie is identical on all hosts (verify with show_cookies task)
- Python 2.6+ is installed in /usr/local/bin/python
- The RabbitMQ command-line admin is installed in /usr/local/bin/rabbitmqadmin

The license is MIT. Have fun with it.


