# AMQP Dispatcher

A daemon to run AMQP consumers


## Running

    RABBITMQ_HOST=rabbitmq.example.com amqp-dispatcher --config amqp-dispatcher-config.yml

The environment variable `RABBITMQ\_HOSTS` can also be used which will cause
attempt to connect to a host in a random order. The list should be comma separated.

    RABBITMQ_HOSTS=rabbitmq1.example.com,rabbitmq2.example.com

## Consumers

Consumers are a class with 2 required methods: `consume` and `shutdown`. AMQP
Dispatcher will not monkey patch the environment, you will have to do that
yourself.

### `consume`

`consume` is called once for each message being handled. It should take 2
parameters, a proxy for AMQP operations (`amqp`) and the message (`msg`).


### `shutdown`

`shutdown` is called before the instance of the consumer is removed. It takes a
single argument `exception` which may be `None`. If your consumer raises an
exception while consuming the `shutdown` method will be called. Once `shutdown`
is finished a new instance of your consumer will be created to replace the one
that raised the exception. If you would like to rate limit instance replacement
you can call `gevent.sleep(X)` to sleep for `X` seconds after a failure.


### Example

    class Consumer(object):

        def __init__(self):
            self.init_msg = "I've been initiliazed"

        def consume(self, amqp, msg):
            print 'Consuming message', msg.body
            gevent.sleep(1)
            val = random.random()
            if val > .8:
                print 'publishing'
                amqp.publish('test_exchange', 'test_routing_key', {}, 'New body!')
            if val < .5:
                raise ValueError()
            print 'Done sleeping'
            amqp.ack()

        def shutdown(self, exception=None):
            print 'Shut down'


## Configuration

AMQP Dispatcher will read environment variable for connection information and a
YAML file for worker configuration.

### Environment Variables

- `RABBITMQ_URL`: Connection string of the form `amqp://USER:PASS@HOST:PORT/VHOST`, `RABBITMQ_URL` is present, all other environment variables are ignored
- `RABBITMQ_HOSTS` - Comma separated list of hosts to connect to
- `RABBITMQ_HOST`  - Host to connect to
- `RABBITMQ_USER`  - Username to connect with (default is `guest`)
- `RABBITMQ_PASS`  - Password to connect with (default is `guest`)
- `RABBITMQ_VHOST` - Virtual host to use (default is `/`)

### Startup Configuration

If you need to perform custom actions (configure your logging, create initial objects) you can add a startup handler.

This is configured in the config yml with the `startup_handler` option.

    startup_handler: amqpdispatcher.example_startup:startup

### Queue configuration

Queues can be created on the fly by amqp dispatcher, and may bind existing exchanges on the fly as well.

There are a few obvious constraints:

* To create a non-passive queue (typical behavior) the current user must have `configure=queue` permission
* To bind to an exchange, the current user must have `read` permission on the binding exchange

##### Required

* `queue`: name of the queue

##### Optional Parameters

* `durable`: queue created in "durable" mode (default = True)
* `auto_delete`: queue created in "auto_delete" mode (default = False), meaning
it will be deleted automatically once all consumers disconnect from it (e.g. on restart)
* `exclusive`: queue created in "exclusive" mode (default = False) meaning it will only be accessible by this process
* `x_dead_letter_exchange`: name of dead letter exchange
* `x_dead_letter_routing_key`: dead letter routing key
* `x_max_length`: maximum length of ready messages. (default = INFINITE)
* `x_expires`: How long a queue can be unused for before it is automatically deleted (milliseconds) (default=INFINITE)
* `x_message_ttl`: How long a message published to a queue can live before it is discarded (milliseconds) (default=INFINITE)

##### Bindings

`bindings`  should contain a list of `exchange`/`routing_key` pairs and defines the binding for the queue (there can be multiple)

A complete configuration example would look like:

    queues:
      - queue: notify_mat_job
        durable: true
        auto_delete: false
        passive: true
        exclusive: false
        x_dead_letter_exchange: null
        x_dead_letter_routing_key: null
        x_max_length: null
        x_expires: null
        x_message_ttl: null
        bindings:
          - exchange: notify
            routing_key: transaction.*
          - exchange: notify
            routing_key: click.*

      - queue: notify_apsalar_job
        bindings:
          - exchange: notify
            routing_key: transaction.*
          - exchange: notify
            routing_key: click.*

### Worker configuration

Workers are autoloaded when AMQP Dispatcher starts. This means your worker must
be importable from the environment.

A complete configuration example would look like:

    consumers:
      - consumer: workers.module:Consumer
        consumer_count: 1
        queue: test_queue
        prefetch_count: 2
      - consumer: workers.module_2:Consumer
        consumer_count: 2
        queue: test_queue_2
        prefetch_count: 10


`prefetch_count` is the AMQP `prefetch_count` when consuming. The
`consumer_count` is the number of instances of your consumer to handle messages
from that queue.  Connection pools are highly recommended.
MySQL will require the [MySQL
Connector](http://pypi.python.org/pypi/mysql-connector-python) instead of
`mysqldb` in order for gevent to switch properly.

Pools can be created and attached to the consumer class during the `__init__`. Example with SQLAlchemy

    class Consumer(object):

        session_maker = None

        def __init__(self):
            self.session = None

            if Consumer._engine is None:
                print 'Creating session maker'
                Consumer._engine = create_engine(...)
                Consumer.sessionmaker = sessionmaker(bind=Consumer._engine)

And then a session created during the consume method.

        def consume(self, proxy, msg):
            session = self.sessionmaker()
            # Do something with the session
            session.close()

# Logging

Logging is performed on the logger `amqp-dispatcher`. The RabbitMQ connection
provided by Haigha will log on `amqp-dispatcher.haigha`.
