import redis
from rq import Queue, SimpleWorker

conn = redis.from_url("redis://:myredissecret@localhost:6379/0")
q = Queue("fitcv", connection=conn)
w = SimpleWorker([q], connection=conn)
w.work()
