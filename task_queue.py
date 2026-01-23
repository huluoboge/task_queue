import threading
import queue
from typing import Callable

class TaskQueue:
    def __init__(self):
        self.tasks = queue.Queue()

    def pushTask(self, task: Callable):
        self.tasks.put(task)

    def popTask(self) -> Callable:
        return self.tasks.get()

    def empty(self) -> bool:
        return self.tasks.empty()

class BoundedTaskQueue:
    def __init__(self, capacity: int = 20):
        self.capacity = capacity
        self.tasks = queue.Queue(maxsize=capacity)

    def setCapacity(self, capacity: int):
        if not self.tasks.empty():
            raise RuntimeError("setCapacity must be called before pushing tasks")
        self.capacity = capacity
        self.tasks = queue.Queue(maxsize=capacity)
    def pushTask(self, task: Callable):
        self.tasks.put(task)   # 阻塞直到有空间（等价 cv_producer）

    def popTask(self) -> Callable:
        return self.tasks.get()

    def empty(self) -> bool:
        return self.tasks.empty()

class ThreadPool:
    def __init__(self, num_threads, task_queue,
                 task_counter_ref, done_cv: threading.Condition):
        self.task_queue = task_queue
        self.task_counter_ref = task_counter_ref
        self.done_cv = done_cv
        self.stop = False
        self.workers = []

        for _ in range(num_threads):
            t = threading.Thread(target=self._worker)
            t.start()
            self.workers.append(t)

    def _worker(self):
        while True:
            task = self.task_queue.popTask()
            if self.stop:
                break
            task()
            self.taskFinished()

    def taskFinished(self):
        with self.done_cv:
            self.task_counter_ref[0] -= 1
            if self.task_counter_ref[0] == 0:
                self.stopAll()
                self.done_cv.notify_all()

    def stopAll(self):
        if not self.stop:
            self.stop = True
            for _ in self.workers:
                self.task_queue.pushTask(lambda: None)

    def join(self):
        for t in self.workers:
            t.join()


class ThreadPoolEx:
    def __init__(self, num_threads, queue_cls=TaskQueue):
        self.taskQueue = queue_cls()
        self.task_counter = [0]
        self.done_cv = threading.Condition()
        self.threadPool = ThreadPool(
            num_threads,
            self.taskQueue,
            self.task_counter,
            self.done_cv
        )

    def setTaskCount(self, n: int):
        self.task_counter[0] = n

    def pushTask(self, task: Callable):
        self.taskQueue.pushTask(task)

    def wait(self):
        with self.done_cv:
            self.done_cv.wait_for(lambda: self.task_counter[0] == 0)
        self.threadPool.join()

class CurrentThread:
    def __init__(self, task_queue, task_counter_ref, done_cv):
        self.task_queue = task_queue
        self.task_counter_ref = task_counter_ref
        self.done_cv = done_cv
        self.stop = False

    def run(self):
        while True:
            task = self.task_queue.popTask()
            if self.stop:
                break
            task()
            self.taskFinished()

    def taskFinished(self):
        with self.done_cv:
            self.task_counter_ref[0] -= 1
            if self.task_counter_ref[0] == 0:
                self.stopAll()
                self.done_cv.notify_all()

    def stopAll(self):
        if not self.stop:
            self.stop = True
            self.task_queue.pushTask(lambda: None)

class CurrentThreadEx:
    def __init__(self, queue_cls=TaskQueue):
        self.taskQueue = queue_cls()
        self.task_counter = [0]
        self.done_cv = threading.Condition()
        self.currentThread = CurrentThread(
            self.taskQueue,
            self.task_counter,
            self.done_cv
        )

    def setTaskCount(self, n: int):
        self.task_counter[0] = n

    def pushTask(self, task: Callable):
        self.taskQueue.pushTask(task)

    def run(self):
        self.currentThread.run()

class Stage:
    def __init__(self, name, num_workers, capacity, func):
        self.name = name
        self.func = func
        self.queue = BoundedTaskQueue(capacity)
        self.pool = ThreadPoolEx(num_workers, lambda: self.queue)
        self.next = None   # 由 chain 设置

    def setTaskCount(self, n):
        self.pool.setTaskCount(n)

    def push(self, index):
        self.queue.pushTask(lambda i=index: self._run(i))

    def _run(self, index):
        self.func(index)
        if self.next:
            self.next.push(index)

    def wait(self):
        self.pool.wait()

def chain(stage_a, stage_b):
    stage_a.next = stage_b
    return stage_b

