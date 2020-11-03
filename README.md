# Python 3 Website Health Monitor #

A Python 3.8 application to monitor website availability and send the health data to a Kafka (hosted on `Aiven`) topic using a Producer, read data from `Kafka` using a Consumer, and writing records into a `PostgreSQL` database (also in `Aiven`).

This implementation extensively uses Python's `asyncio` for efficient single-process single-threaded concurrency.

## Overview ##

The application consists of a Producer that monitors the status of a URL and produces metrics, which are dumped into a `asyncio Queue` in stringified `JSON` format. 

As of now the following metrics are recorded:

* `timestamp` : of the query
* `response data` : the data sent as the response to the HTTP GET request
* `response status` : the status code of the response
* `response time` : the time it took from request to response

The aforementioned `JSON` strings are obtained from the `asyncio Queue` by a Consumer, and these are then sent to the Kafka endpoint, to the appropriate topic, by an `AIOKafkaProducer`. 

Finally, an `AIOKafkaConsumer` is used to get the messages from the topic, and write them as records into the appropriate `PostgreSQL` database's table.

### Usage ### 

The recommended way to execute this application is to first set up a Python 3.8 virtual environment, and use the requirements.txt file with pip to install correct versions of packages.

Please refer to the appropriate documentation for your distribution/OS in order to install PostgreSQL and its dependencies, for example https://www.postgresql.org/download/linux/ubuntu/

The primary dependency for `main.py` is `config.json` - which contains the configuration parameters to execute the application. As of this writing, the parameters specified in `config.json` are:

* url_to_monitor
* sleep_duration
* pg_uri
* kafka_bootstrap
* kafka_topic

The only other required files for this application are the SSL files needed to create the SSL context for `AIOKafkaProducer` and `AIOConsumer`

```
context = create_ssl_context(
        cafile="./ssl_kafka/ca.pem",
        certfile="./ssl_kafka/service.cert",
        keyfile="./ssl_kafka/service.key"
    )
```


#### Example Response ####

```
/home/pimeson/PyVirtualEnvs/Py38_default/bin/python /home/pimeson/Projects/UrlStatus/main.py
Message produced from URL health monitor: {"timestamp": 1604406256.275848, "response_data": "{\n  \"uuid\": \"c96b87f7-03c4-4119-b344-6dfda6e65654\"\n}\n", "response_status": 200, "response_time": 0.9919679164886475}

AIOKafka Consumer fetched: b'{"timestamp": 1604406256.275848, "response_data": "{\\n  \\"uuid\\": \\"c96b87f7-03c4-4119-b344-6dfda6e65654\\"\\n}\\n", "response_status": 200, "response_time": 0.9919679164886475}'

Message produced from URL health monitor: {"timestamp": 1604406262.217199, "response_data": "{\n  \"uuid\": \"fc7f2464-b892-4d45-854e-bc8de391da36\"\n}\n", "response_status": 200, "response_time": 0.9392151832580566}

AIOKafka Consumer fetched: b'{"timestamp": 1604406262.217199, "response_data": "{\\n  \\"uuid\\": \\"fc7f2464-b892-4d45-854e-bc8de391da36\\"\\n}\\n", "response_status": 200, "response_time": 0.9392151832580566}'

Message produced from URL health monitor: {"timestamp": 1604406268.168641, "response_data": "{\n  \"uuid\": \"b17da339-5ba3-4043-9304-b449e3c9f634\"\n}\n", "response_status": 200, "response_time": 0.9502818584442139}

AIOKafka Consumer fetched: b'{"timestamp": 1604406268.168641, "response_data": "{\\n  \\"uuid\\": \\"b17da339-5ba3-4043-9304-b449e3c9f634\\"\\n}\\n", "response_status": 200, "response_time": 0.9502818584442139}'

Message produced from URL health monitor: {"timestamp": 1604406274.258424, "response_data": "{\n  \"uuid\": \"2cf23040-5306-43fd-8833-1a1ffe44dbe3\"\n}\n", "response_status": 200, "response_time": 1.087674617767334}

AIOKafka Consumer fetched: b'{"timestamp": 1604406274.258424, "response_data": "{\\n  \\"uuid\\": \\"2cf23040-5306-43fd-8833-1a1ffe44dbe3\\"\\n}\\n", "response_status": 200, "response_time": 1.087674617767334}'

```

Verifying the database entries: 

The following code was used to quickly verify that the records were indeed being inserted into the correct database:

```
>>> import psycopg2       
>>> uri = "postgres://avnadmin:hx3a257t95wpn7i1@pg-20a9a7ba-ab-b1c2.aivencloud.com:21774/exercise1?sslmode=require"
>>> con = psycopg2.connect(uri)
>>> cur = con.cursor()
>>> cur.execute("SELECT * FROM health_data")
>>> rows = cur.fetchall()
>>> for row in rows:
...   print(f"ID={row[0]}, timestamp={row[1]}, data={row[2]}, status={row[3]}, time={row[4]}")
...
```

The following output was received (note that some results were removed for brevity):

```
ID=1, timestamp=1604338351.303779, data={
  "uuid": "16a27ddb-6b81-4ef1-a035-a985c4ca150c"
}
, status=200, time=0.9819052219390869
ID=2, timestamp=1604338352.260545, data={
  "uuid": "5cab35fb-7d52-4090-bf2b-8a1d469661bc"
}
, status=200, time=0.9532411098480225
ID=3, timestamp=1604338952.471771, data={
  "uuid": "88b6fa21-a6ff-463a-ae84-6bacebc3ac33"
}
, status=200, time=0.9851107597351074
ID=4, timestamp=1604338953.41354, data={
  "uuid": "1f1e58b8-baf3-4ad3-8ab7-da3b6e827dd4"
}
, status=200, time=0.9408714771270752
...
, status=200, time=0.9413642883300781
ID=67, timestamp=1604406256.275848, data={
  "uuid": "c96b87f7-03c4-4119-b344-6dfda6e65654"
}
, status=200, time=0.9919679164886475
ID=68, timestamp=1604406262.217199, data={
  "uuid": "fc7f2464-b892-4d45-854e-bc8de391da36"
}
, status=200, time=0.9392151832580566
ID=69, timestamp=1604406268.168641, data={
  "uuid": "b17da339-5ba3-4043-9304-b449e3c9f634"
}
, status=200, time=0.9502818584442139
ID=70, timestamp=1604406274.258424, data={
  "uuid": "2cf23040-5306-43fd-8833-1a1ffe44dbe3"
}
, status=200, time=1.087674617767334
```


## References ##

* https://docs.aiohttp.org/en/stable/client_quickstart.html
* https://github.com/mosquito/aiofile
* https://aiokafka.readthedocs.io/en/stable/examples/ssl_consume_produce.html
* https://github.com/aio-libs/aiokafka/tree/master/examples
* https://help.aiven.io/en/articles/489572-getting-started-with-aiven-kafka
* https://help.aiven.io/en/articles/489573-getting-started-with-aiven-postgresql
* https://www.postgresql.org/download/linux/ubuntu/
