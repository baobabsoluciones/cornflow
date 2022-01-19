ROADEF - Inventory Routing Problem
==================================

Problem
-------
A vendor has to manage the inventories of its customers and decide when and how to deliver to them in order to avoid stock-outs. He has to create the delivery routes, assign them to a driver, a trailer, and a starting time, and to decide what quantity of product will be delivered to each customer on every route. The objective to minimize is the total cost of all the shifts.

Decisions
---------
A set of routes (ordered list of locations) associated to a trailer, a driver and a departure time. Each step of the route is associated to a quantity, corresponding to the quantity of product delivered (if the location is a customer) or loaded (if the location is a source).
The decision is subject to several constraints:

- A driver must have time to rest between two shifts
- A driver has a maximum driving duration
- No stock-outs are allowed
- The future consumption of all customers is known at all times. The shift swill therefore be planned all at once for the entire time horizon
- A shift may alternate loading and deliveries. Thus, a shift is not limited by the capacity of the vehicle ; only the succession of deliveries between two sources is
- The base (i.e. the starting and ending place of all shifts) is not always situated in the same place as the sources. Therefore, a trailer leaving the base fora shift is not necessarily full
- The trailers have different capacities
- The loading and unloading times are fixed. Those times must be included in the schedule of each shift.
- Drivers are paid from their departure of the base until they return to the base

Input
-----
- The duration of the time horizon, that is, the number of hours studied

- The index of the base (that is, the location from where all of the shifts departure and where they always finish). 

- Information about the sources, that is:

  - Their indices
  - The minimum time the trailer has to stay at the source to safely load the product
    
- Information about the customers, that is:

  - Their indices
  - The minimum time the trailer has to stay at the customer to safely deliver the product
  - The capacity of their tanks
  - The forecast of their consumption of product at each hour of the time horizon
  - The initial quantity of product in their tanks
    
- Information about the trailers, that is:

  - Their indices
  - Their capacities
  - The initial quantity of product in their tanks
  - The cost per unit of distance travelled with the trailer (i.e. the cost per km)
    
- Information about the drivers, that is:

  - Their indices
  - The maximum duration they are allowed to drive
  - The minimum duration of their breaks between two shifts
  - Their salary per working hour
    
- A time matrix and a distance matrix indicating respectively the time and the distance between each pair of location 

Output
------
| A set of shifts composed of:
- A route, i.e. a list of steps composed of:

  - A location
  - A quantity of product
    
- A driver
- A trailer
- A departure time

