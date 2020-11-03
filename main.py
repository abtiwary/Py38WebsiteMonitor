#!/usr/bin/env python3

# A Python 3.8 application to monitor website availability and send the health data to
# a Kafka (hosted on Aiven) topic using a Producer, read data from Kafka using a
# Consumer, and writing records into a PostgreSQL database (also in Aiven).

# Principal author: Abhishek Tiwary
#                   ab dot tiwary at gmail.com

import sys
import time
import json
import asyncio
import aiohttp
import aiofile
import psycopg2

from datetime import datetime
from aiokafka import AIOKafkaProducer
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context

# This Producer function implements a system that monitors website availability
# and produces metrics, which are dumped asynchronously into an asyncio queue.
# The information written to the queue is stringified JSON
async def Producer(url: str, q: asyncio.Queue, sleep_duration: int):
    health_data = {}
    while True:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.get(url) as resp:
                resp_text = await resp.text()
                resp_status = resp.status
                end_time = time.time()
                health_data["timestamp"] = datetime.now().timestamp()
                health_data["response_data"] = resp_text
                health_data["response_status"] = resp_status
                health_data["response_time"] = end_time - start_time
                health_str = json.dumps(health_data)
                await q.put(health_str)
                await asyncio.sleep(sleep_duration)

# The Consumer function asynchronously consumes from the queue, which is written to
# by the previous Producer function. The stringified JSON read from the queue is then
# send to the appropriate Kafka topic as bytes.
async def Consumer(q: asyncio.Queue, kproducer: AIOKafkaProducer):
    await kproducer.start()

    while True:
        message = await q.get()
        print(f"Message produced from URL health monitor: {message}\n")

        # also produce to kafka
        msg = await kproducer.send_and_wait('exercise1', str(message).encode())
        #print(f"AIOKafka Producer produced: {msg}\n")
        await asyncio.sleep(0.05)

# The KConsumer function uses the AIOKafkaConsumer to read from an appropriate
# topic - in this case metrics in JSON format.
# These are then committed into the health_data table, in the exercise1 database
# (PostgreSQL database on Aiven)
async def KConsumer(kconsumer: AIOKafkaConsumer, pg_con, pg_cur):
    await kconsumer.start()

    while True:
        async for msg in kconsumer:
            print(f"AIOKafka Consumer fetched: {msg.value}\n")
            try:
                json_msg = json.loads(msg.value)
                pg_cur.execute(
                    "INSERT INTO health_data (timestamp, data, status, response_time) VALUES (%s, %s, %s, %s)",
                    (
                        json_msg["timestamp"],
                        json_msg["response_data"],
                        json_msg["response_status"],
                        json_msg["response_time"]
                    )
                )
                pg_con.commit()
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"An exception occurred while attempting to write metrics to Postgres {e}", file=sys.stderr)


async def main():
    config_data = None
    config = None
    # read the configuration from file
    try:
        async with aiofile.AIOFile("./config.json", 'rb') as afp:
            config_data = await afp.read()
        #print(config_data)
        config = json.loads(config_data)
    except Exception as e:
        print(f"the attempt to read the config file failed with: {e}", file=sys.stderr)
        sys.exit(1)

    # SSL context for AIOKafka
    context = create_ssl_context(
        cafile="./ssl_kafka/ca.pem",
        certfile="./ssl_kafka/service.cert",
        keyfile="./ssl_kafka/service.key"
    )

    kproducer = AIOKafkaProducer(bootstrap_servers=[config["kafka_bootstrap"]],
                                 security_protocol='SSL',
                                 ssl_context=context)

    kconsumer = AIOKafkaConsumer(config["kafka_topic"],
                                 auto_offset_reset="earliest",
                                 bootstrap_servers=[config["kafka_bootstrap"]],
                                 security_protocol='SSL',
                                 ssl_context=context)

    q = asyncio.Queue()

    # postgres
    # note:
    # cur.execute("CREATE TABLE health_data (id serial PRIMARY KEY, timestamp varchar, data varchar, status integer, response_time varchar);")
    pg_con = psycopg2.connect(config["pg_uri"])
    pg_cur = pg_con.cursor()

    producers = [asyncio.create_task(Producer(config["url_to_monitor"], q, config["sleep_duration"]))]
    consumers = [asyncio.create_task(Consumer(q, kproducer)),
                 asyncio.create_task(KConsumer(kconsumer, pg_con, pg_cur))]

    try:
        await asyncio.gather(*producers)
        await q.join()
    # handle Control+C and stop gracefully
    except KeyboardInterrupt:
        for p in producers:
            p.cancel()

        for c in consumers:
            c.cancel()
    finally:
        await kproducer.stop()
        await kconsumer.stop()
        pg_cur.close()
        pg_con.close()


if __name__ == "__main__":
    asyncio.run(main())



# references:
# https://docs.aiohttp.org/en/stable/client_quickstart.html
# https://github.com/mosquito/aiofile
# https://aiokafka.readthedocs.io/en/stable/examples/ssl_consume_produce.html
# https://github.com/aio-libs/aiokafka/tree/master/examples
# https://help.aiven.io/en/articles/489572-getting-started-with-aiven-kafka
# https://help.aiven.io/en/articles/489573-getting-started-with-aiven-postgresql
# https://www.postgresql.org/download/linux/ubuntu/


# import psycopg2
# >>> uri = "postgres://avnadmin:hx3a257t95wpn7i1@pg-20a9a7ba-ab-b1c2.aivencloud.com:21774/exercise1?sslmode=require"
# >>> con = psycopg2.connect(uri)
# >>> cur = con.cursor()
# >>> cur.execute("SELECT * FROM health_data")
# >>> rows = cur.fetchall()
# >>> for row in rows:
# ...   print(f"ID={row[0]}, timestamp={row[1]}, data={row[2]}, status={row[3]}, time={row[4]}")
# ...
#
