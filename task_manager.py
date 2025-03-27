import heapq
import time
import json
import stations.stations as stations
import discordbot
import datetime
from threading import Lock, Thread 

global scheduler

class SingletonMeta(type):

    _instances = {}

    _lock: Lock = Lock()

    def __call__(cls,*args,**kwargs):

        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args,**kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]

class priority_queue_exc:
    def __init__(self):
        self.queue = []  

    def add(self, task, priority, execution_time):
        heapq.heappush(self.queue, (execution_time, len(self.queue), priority, task))

    def pop(self):
        if not self.is_empty():
            return heapq.heappop(self.queue)
        return None

    def peek(self):
        if not self.is_empty():
            return self.queue[0]
        return None

    def is_empty(self):
        return len(self.queue) == 0
    
class priority_queue_prio:
    def __init__(self):
        self.queue = []  

    def add(self, task, priority, execution_time):
        heapq.heappush(self.queue, (priority, execution_time, len(self.queue), task))

    def pop(self):
        if not self.is_empty():
            return heapq.heappop(self.queue)
        return None

    def peek(self):
        if not self.is_empty():
            return self.queue[0]
        return None

    def is_empty(self):
        return len(self.queue) == 0

class task_scheduler(metaclass=SingletonMeta):
    def __init__(self):
       if not hasattr(self, 'initialized'):  
            self.active_queue = priority_queue_prio() 
            self.waiting_queue = priority_queue_exc()  
            self.initialized = True 

    def add_task(self, task):
        
        if not getattr(task, 'has_run_before', False):
            next_execution_time = time.time()  
        else:
            next_execution_time = time.time() + task.get_requeue_delay()  

        task.has_run_before = True
    
        self.waiting_queue.add(task, task.get_priority_level(), next_execution_time)
        print(f"Added task {task.name} to waiting queue ") # might need to remove this if you have LOADS OF stations causing long messages

    def print_waiting_queue(self):
        if self.waiting_queue.is_empty():
            discordbot.queue_write("waiting_queue is empty.", "wait")
        else:
            discordbot.queue_write("Current waiting_queue:", "wait")
            for i, (exec_time, _, priority, task) in enumerate(self.waiting_queue.queue):
                if i >= 5: # preventing the limit on discord message length
                    discordbot.queue_write(f"...and {len(self.waiting_queue.queue) - 5} more tasks.", "wait")
                    break
                discordbot.queue_write(f"Task {i+1} Name: {task.name} Priority: {priority} Next Execution Time: <t:{int(exec_time)}:R>","wait")

    def print_active_queue(self):
        if self.active_queue.is_empty():
            discordbot.queue_write(" active_queue is empty.","active")
        else:
            discordbot.queue_write("Current active_queue:","active")
            
            for i, (priority,exec_time,  _,task) in enumerate(self.active_queue.queue):  
                if i >= 5: # preventing the limit on discord message length
                    discordbot.queue_write(f"...and {len(self.active_queue.queue) - 5} more tasks.", "active")
                    break
                discordbot.queue_write(f"Task {i+1} Name: {task.name} Priority: {priority} Currently waiting for execution","active")
            
    def run(self):
        while True:
            current_time = time.time()

            self.move_ready_tasks_to_active_queue(current_time)
            
            self.print_active_queue()
            self.print_waiting_queue()
            if not self.active_queue.is_empty():
                self.execute_task(current_time)
            else:
                time.sleep(5)

    def move_ready_tasks_to_active_queue(self, current_time):
        
        while not self.waiting_queue.is_empty():
            task_tuple = self.waiting_queue.peek()
            exec_time, _, priority, task = task_tuple

            if exec_time <= current_time:
                self.waiting_queue.pop()  
                self.active_queue.add(task, priority, exec_time)  
                
            else:
                break  

    def execute_task(self, current_time):
        
        task_tuple = self.active_queue.pop()  
        exec_time,priority , _, task = task_tuple

        if exec_time <= current_time:
            discordbot.logger(f"Executing task: {task.name}")
            task.execute()  
    
            if task.name != "pause":
                self.move_to_waiting_queue(task)
            else:
                print("pause task skipping adding back ")
        else:
            
            self.active_queue.add(task, priority, exec_time)

    def move_to_waiting_queue(self, task):
        discordbot.logger(f"adding {task.name} to waiting queue" ) 
        next_execution_time = time.time() + task.get_requeue_delay()
        priority_level = task.get_priority_level()
        self.waiting_queue.add(task,priority_level , next_execution_time)



def load_resolution_data(file_path):
    try:
        with open(file_path, 'r') as file:
            data = file.read().strip()
            if not data:
                discordbot.logger(f"warning: {file_path} is empty no tasks added.")
                return []
            return json.loads(data)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"error loading JSON from {file_path}: {e}")
        return []


def main():
    global scheduler
    scheduler = task_scheduler()
    
    pego_data = load_resolution_data("json_files/pego.json")
    for entry_pego in pego_data:
        name = entry_pego["name"]
        teleporter = entry_pego["teleporter"]
        delay = entry_pego["delay"]
        task = stations.pego_station(name,teleporter,delay)
        scheduler.add_task(task)

    gacha_data = load_resolution_data("json_files/gacha.json")
    for entry_gacha in gacha_data:
        name = entry_gacha["name"]
        teleporter = entry_gacha["teleporter"]
        direction = entry_gacha["side"]
        resource = entry_gacha["resource_type"]
        if resource == "collect":
            depo = entry_gacha["depo_tp"]
            task = stations.snail_pheonix(name,teleporter,direction,depo)
        else:
            task = stations.gacha_station(name, teleporter, direction)
        scheduler.add_task(task)
        
    scheduler.add_task(stations.render_station())
    discordbot.logger("scheduler now running")
    scheduler.run()

if __name__ == "__main__":
    time.sleep(2)
    main()


