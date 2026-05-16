import time

class TimeEngine:
    def __init__(self):
        self.current_step = 0

    def step(self):
        self.current_step += 1
        print(f"Simulation Step: {self.current_step}")
        return self.current_step
