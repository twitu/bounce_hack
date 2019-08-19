# Bounce Hack
This is my experiment for Bounce Hackathon 1.0. My idea is to solve supply demand issues in ride-sharing and micro-mobility space by dynamically redistributing the vehicle, in this scooters using large vehicles like trucks.

I wrote this module to simulate a probabilistic model for customers, scooters and trucks. I wanted to make it look pretty, so I added visualization for the road networks and animation for the moving points. 

It took a lot of libraries and SOing to get this to work, I will add a few important links in the [Reference section](#references)

## Design overview
The unit for time for the simulation is a `turn`. Each turn also updates a frame in the animation. For sake of simplicity (mainly lack of time), I have considered the distance between each node in the road network, to be equal. Although the road networks is sampled from a real place, it is essentially a square grid for this simulation.

> `scooter_simulation.SimulateScooters`  

Scooters can hailed from a metro station. There is a fixed influx of customers (`IN_RATE`), who are equally probable (`OFFICE_PROB`) to go to any one of the offices. Each customer will wait for a fixed number of turns (`WAITING_TIME`). Total number of scooters in the map is fixed (`SCOOTERS_TOTAL`). Scooters parked at offices have a probability (`REPLENISH`), intentionally kept small, of returning to the metro station to simulate a small amount of traffic coming back from the offices. The `turn` method updates the scooter positions in each turn.

> `truck_simulation.SimulateTrucks`  

The number of trucks (`NUMBER`), and carrying capacity (`CAPACITY`) can be changed. The brute `brute_algo` starts giving significant delays with 4 or more trucks. I have written two simple scoring functions. The `greedy_score` tries to maximize profit, while the `aging_score` prevents starvation by increasing priority of unused scooters. A third scoring function `combined_score` tries to combine the two scores in a given ratio.

> `bounce_simulation.BounceSimulation`  

`setup_plot` sets the stage for the simulation. It adds 3 artists to the figure, `lc` which draws the roads, `plot_scooters` which draws scooter positions and `plot_trucks` which draws trucks.

`update_plot` is called for every frame. It firsts calls updates scooter state for the turn. It then updates the artist for the scooters with new positions, sized and colors. Next it calculates the path for idle trucks and updates state for all trucks, after which updates the artist plotting the trucks.

`update_plot` also collects data logged by `SimulateTrucks` and `SimulateScooters`. It stores the logs as a list of lists. The list is flattened before passing it to `VisualizeData`.

> `visualize_data.VisualizeData`

Similar to `BounceSimulation`, used `setup_plot` and `animate`. `animate` clears the the figure, appends an additional data point and re-renders the figure, a crude but effective method.

## References
