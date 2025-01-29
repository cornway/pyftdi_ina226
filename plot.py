import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import time
from collections import deque

from dataclasses import dataclass

@dataclass
class RealTimePlotParams:
    xlabel: str = "Xlabel",
    ylabel: str = "Ylabel",
    title: str = "Title"

class RealTimePlot:
    def __init__(self, params: list, winsize, interval, generator):

        n = len(params)

        self.winsize = winsize
        self.interval = interval
        self.generator = generator

        self.params = params
        self.fig, self.axes = plt.subplots(n)

        self.data = []
        self.timestamps = []
        for p in self.params:
            self.data.append( deque(maxlen=self.winsize) )
            self.timestamps.append( deque(maxlen=self.winsize) )

        self.start_time = time.time()  # Initial timestamp for X axis

        self.lines = []
        self.text_boxes = []
        for i, p in enumerate(self.params):
            line, = self.axes[i].plot([], [], lw=2)
            self.lines.append( line )
            self.axes[i].set_xlabel(p.xlabel)
            self.axes[i].set_ylabel(p.ylabel)
            self.axes[i].set_title(p.title)
            self.axes[i].grid(True)
            self.text_boxes.append(
                self.axes[i].text(
                    0.02, 0.95, "", transform=self.axes[i].transAxes, verticalalignment="top"
                )
            )

    def update_plot_single(self, i, value, current_time):
        new_value = value
        self.data[i].append(new_value)
        self.timestamps[i].append(current_time)

        self.lines[i].set_data(self.timestamps[i], self.data[i])

        if False:
            mean_value = np.mean(self.data) if self.data else 0
            std_dev = np.std(self.data) if self.data else 0
            min_value = np.min(self.data) if self.data else 0
            max_value = np.max(self.data) if self.data else 0
            integral = np.trapz(self.data, self.time_stamps) if len(self.data) > 1 else 0

            # Update the statistics text box
            self.text_box.set_text(
                f"Mean: {mean_value:.2f}\n"
                f"Std Dev: {std_dev:.2f}\n"
                f"Min: {min_value:.2f}\n"
                f"Max: {max_value:.2f}\n"
                f"Integral: {integral:.2f}"
            )

        win_time = self.interval * self.winsize
        self.axes[i].set_xlim(max(0, current_time - win_time), current_time)
        self.axes[i].relim()
        self.axes[i].autoscale_view()

    def update_plot(self, frame):
        current_time = time.time() - self.start_time  # Calculate elapsed time

        values = next(self.generator)

        for i in range(len(self.params)):
            self.update_plot_single(i, values[i], current_time)

        return self.lines

    def run(self):
        ani = animation.FuncAnimation(
            self.fig, self.update_plot, blit=True, interval=self.interval * 1000
        )
        plt.show()

winsize = 1000
interval = 0.02


def generator_1():
    while True:
        yield np.sin(time.time())
        time.sleep(interval)

def generator_2():
    while True:
        yield np.cos(time.time())
        time.sleep(interval)

if __name__ == '__main__':
    params = []

    params.append(
        RealTimePlotParams(
            generator=generator_1(),
            xlabel="Time",
            ylabel="Voltage",
            title=("voltage")
        )
    )

    params.append(
        RealTimePlotParams(
            generator=generator_2(),
            xlabel="Time",
            ylabel="Power",
            title=("Power")
        )
    )

    plot = RealTimePlot(params, winsize, interval)

    plot.run()