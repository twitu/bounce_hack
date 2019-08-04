import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from matplotlib import animation
from matplotlib import style


DATA_POINTS = 5
if __name__ == '__main__':
    with open("data_15fps.txt") as data_file:
        lines = data_file.readlines()
        lines = [float(data) for data in lines]
        customers_served = lines[::DATA_POINTS]
        waiting_time = lines[1::DATA_POINTS]
        customers_dropped = lines[2::DATA_POINTS]
        under_utilization = lines[3::DATA_POINTS]
        truck_utilization = lines[4::DATA_POINTS]

    avg_waiting_time = []
    for (customers, time) in zip(customers_dropped, waiting_time):
        if not customers:
            avg_waiting_time.append(0)
        else:
            avg_waiting_time.append(time/customers)

    def animate(frame):
        xs = range(frame + 1)
        ax1.clear()
        ax1.plot(xs, customers_dropped[:frame+1])
        ax2.clear()
        ax2.plot(xs, avg_waiting_time[:frame+1])
        ax3.clear()
        ax3.plot(xs, under_utilization[:frame+1])
        ax4.clear()
        ax4.plot(xs, truck_utilization[:frame+1])
        ax1.set_title("Customers dropped with time")
        ax2.set_title("Average customer waiting time")
        ax3.set_title("Average idle state per scooter per turn")
        ax4.set_title("Average truck utilzation")

    style.use('bmh')

    fig = plt.figure()
    spec = gridspec.GridSpec(ncols=2, nrows=2, figure=fig)
    ax1 = fig.add_subplot(spec[0, 0])
    ax2 = fig.add_subplot(spec[0, 1])
    ax3 = fig.add_subplot(spec[1, 0])
    ax4 = fig.add_subplot(spec[1, 1])
    plt.subplots_adjust(top=0.92, bottom=0.08, left=0.10, right=0.95, hspace=0.25,
                        wspace=0.35)
    manager = plt.get_current_fig_manager()
    manager.resize(*manager.window.maxsize())
    fig.set_size_inches((13, 7), forward=False)


    # fig, (ax1, ax2, ax3, ax4) = plt.subplots(2, 2)
    # ax1.set_title("Customers dropped with time")
    # ax2.set_title("Average customer waiting time")
    # ax3.set_title("Average idle state per scooter per turn")
    # ax4.set_title("Average truck utilzation")
    # fig.tight_layout()

    ani = animation.FuncAnimation(fig, animate, frames=len(customers_dropped))
    # ani.save('aging_15fps_stats.gif', writer='imagemagick', fps=15, dpi=100)
    plt.show()
