import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib import style


class VisualizeData:
    DATA_POINTS = 4

    def __init__(self, data):
        self.data = data
        self.frames = len(data) // self.DATA_POINTS
        self.avg_waiting_time = self.data[0::self.DATA_POINTS]
        self.customers_dropped = self.data[1::self.DATA_POINTS]
        self.under_utilization = self.data[2::self.DATA_POINTS]
        self.truck_utilization = self.data[3::self.DATA_POINTS]
        self.fig = plt.figure()
        self.ani = animation.FuncAnimation(self.fig, self.animate, init_func=self.setup_plot, frames=self.frames)

    def animate(self, frame):
        xs = range(frame + 1)
        self.ax1.clear()
        self.ax1.plot(xs, self.customers_dropped[:frame + 1])
        self.ax2.clear()
        self.ax2.plot(xs, self.avg_waiting_time[:frame + 1])
        self.ax3.clear()
        self.ax3.plot(xs, self.under_utilization[:frame + 1])
        self.ax4.clear()
        self.ax4.plot(xs, self.truck_utilization[:frame + 1])
        self.ax1.set_title("Customers dropped with time")
        self.ax2.set_title("Average customer waiting time")
        self.ax3.set_title("Average idle state per scooter per turn")
        self.ax4.set_title("Average truck utilzation")

    def setup_plot(self):
        style.use('bmh')
        spec = gridspec.GridSpec(ncols=2, nrows=2, figure=self.fig)
        self.ax1 = self.fig.add_subplot(spec[0, 0])
        self.ax2 = self.fig.add_subplot(spec[0, 1])
        self.ax3 = self.fig.add_subplot(spec[1, 0])
        self.ax4 = self.fig.add_subplot(spec[1, 1])
        plt.subplots_adjust(top=0.92, bottom=0.08, left=0.10, right=0.95, hspace=0.25,
                            wspace=0.35)
        manager = plt.get_current_fig_manager()
        manager.resize(*manager.window.maxsize())
        self.fig.set_size_inches((13, 7), forward=False)
