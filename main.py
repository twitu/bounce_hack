import random
import sys

from bounce_simulation import BounceSimulation

if __name__ == "__main__":
    random.seed(25)
    simulation = BounceSimulation(with_trucks=False, score_func=sys.argv[1])
    simulation.ani.save('simple_15fps.gif', writer='imagemagick', fps=15)
