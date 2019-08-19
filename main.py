import random
import sys
from itertools import chain

from bounce_simulation import BounceSimulation
from visualize_data import VisualizeData

if __name__ == "__main__":
    """
    Pass 'greedy', 'aging' or 'combined' as input argument, to choose
    scoring function
    """
    random.seed(25)
    simulation = BounceSimulation(score_func=sys.argv[1])
    simulation.ani.save('bounce_simulation.gif', writer='imagemagick', fps=10)
    visualize = VisualizeData(list(chain.from_iterable(simulation.data)))
    visualize.ani.save('data_simulation.gif', writer='imagmagick', fps=10)
