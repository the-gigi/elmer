Elmer
-----
A Fabric file called rabbit.py to control a RabbitMQ cluster

The cluster hosts, user and password are defined in config.py

You can start and stop the service on remote hosts
You can execute any rabbitmqctl command using the rmq method

Finally you can create a whole cluster from scratch and administer it.

The script assumes the following:

- The cluster nodes is a *nix boxes
- RabbitMQ is installed in the default location using the default configuration
- The node is called rabbit@<host>
- The Erlang cookie is identical on all hosts (verify with show_cookies task)
- Python 2.6+ is installed in /usr/local/bin/python
- The RabbitMQ command-line admin is installed in /usr/local/bin/rabbitmqadmin