from dotenv import load_dotenv
from redis import Redis
from rq import Worker, Queue
import os

load_dotenv()
env = os.environ

REDIS_URL = env.get("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(REDIS_URL)

q = Queue("emails", connection=redis_conn)
worker = Worker([q], connection=redis_conn)
worker.work()
