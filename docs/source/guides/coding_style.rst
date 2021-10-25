Coding style and rules
============================

The following rules and notation come from examples in PR-revisions that we think can become common rules. Each rule will have an example and a description.


Commenting out code
-------------------------

Having commented code makes no sense. It should be eliminated from the commit altogether. If for some reason you fear losing the piece of code in the future, remember that it will be present in the git history if it has taken part of the **master branch** at some point:

.. code-block:: javascript

  /* LMapPoints () {
    var points = []
    var offsetCustomers = 1 + this.instance.data.sources.length
    for (var point of this.instance.lonLat) {
      var newPoint = { x: point.x, y: point.y, location: point.location }
      if (point.location === 0) {
        newPoint.type = 'B'
      } else if (point.location < 1 + this.instance.data.sources.length) {
        newPoint.type = 'S'
      } else {
        newPoint.type = 'C'
        newPoint.capacity = this.instance.data.customers[point.location - offsetCustomers].Capacity
      }
      points.push(newPoint)
    }
    return points
  } */


Argument type checking
-------------------------

Both python and javascript can be very lax with type validations in arguments and interfaces. This is usually very practical but it can sometimes lead to the following (incorrect) "runtime validations" inside a function:

.. code-block:: javascript

    export class Experiment extends ExperimentCore {
      static MyInstance = Instance
      static MySolution = Solution

      constructor (instance, solution) {
        super(instance, solution)

        if (this.solution != null) {
          this.colors = this.solution.colors
        }

        this.sizeCustomerPoint = 10
        this.sizeBasePoint = 30
        this.sizeSourcePoint = 20
        if (this.instance != null) {
          this.offsetCustomers = this.instance.data.sources.length + 1
        }
        this.colorBase = '#65A0D1'
        this.colorSource = '#D35A5A'

        if (this.instance != null) {
          this.horizon = this.instance.data.parameters.horizon
          this.unit = this.instance.data.parameters.unit
        }
      }


In the example, we're checking for the existence of instance and solution when creating a new Experiment.

In fact, these validations should not be done inside. Experiment is correct to assume that when it requires an instance and a solution, it should get one as arguments. If the arguments were optional, then they should appear with a default value in the method. In practice, we *want* Experiment to fail when there are incorrect (unexpected) arguments.

The actual validations should be done outside (before) the creation of the Experiment so as to be sure to provide Experiment always with an instance and a solution.

These kinds of validations can be done in javascript (python) with the use of TypeScript (python type-hints). While TypeScript is not yet present in Cornflow-app, python type-hints are very well present in cornflow-server and cornflow-client.

In this case, the correct code would be the same but without ifs:

.. code-block:: javascript

    export class Experiment extends ExperimentCore {
      static MyInstance = Instance
      static MySolution = Solution

      constructor (instance, solution) {
        super(instance, solution)

        this.colors = this.solution.colors

        this.sizeCustomerPoint = 10
        this.sizeBasePoint = 30
        this.sizeSourcePoint = 20
          this.offsetCustomers = this.instance.data.sources.length + 1
        this.colorBase = '#65A0D1'
        this.colorSource = '#D35A5A'

        this.horizon = this.instance.data.parameters.horizon
        this.unit = this.instance.data.parameters.unit
      }


Indentation
---------------

original code:

.. code-block:: python

    driver = shift["driver"]
    time_cost = self.instance.get_driver_property(driver, "TimeCost")
    layover_cost = self.instance.get_driver_property(driver, "LayoverCost")

    trailer = shift["trailer"]
    dist_cost = self.instance.get_trailer_property(trailer, "DistanceCost")

    current_stop = None
    layover = False


    for stop in shift["route"]:
        previous_stop = current_stop
        current_stop = stop["location"]
        if stop["layover_before"] == 1:
            layover = True
        if previous_stop is not None:
            distance = self.instance.get_distance_between(
                previous_stop, current_stop
            )
            time = self.instance.get_time_between(previous_stop, current_stop)
            if self.is_source(current_stop):
                time += self.instance.get_source_property(
                    current_stop, "setupTime"
                )
            elif self.is_customer(current_stop):
                time += self.instance.get_customer_property(
                    current_stop, "setupTime"
                )
            total_cost += distance * dist_cost + time * time_cost


    if layover:
        total_cost += layover_cost

In general, excessive indentation makes the code hard to review and understand. One way to do that with an if inside a for is with something like this::

.. code-block:: python

    if previous_stop is None:
        continue # the loop ends here
    # continue with the for-loop as it were an else clause.
    distance = self.instance.get_distance_between(previous_stop, current_stop)

On top of that, if you have all this indentation and long for loops you can just create a function called `_get_route_cost(stop)` and use it inside the function. Something like this:

.. code-block:: python

    def _get_route_cost(self, route, time_cost, layover_cost, dist_cost):

        current_stop = None
        layover = False
        cost = 0

        for stop in route:
            previous_stop = current_stop
            current_stop = stop["location"]
            if stop["layover_before"] == 1:
                layover = True
            if previous_stop is None:
                continue
            distance = self.instance.get_distance_between(
                previous_stop, current_stop
            )
            time = self.instance.get_time_between(previous_stop, current_stop)
            if self.is_source(current_stop):
                time += self.instance.get_source_property(
                    current_stop, "setupTime"
                )
            elif self.is_customer(current_stop):
                time += self.instance.get_customer_property(
                    current_stop, "setupTime"
                )
            cost += distance * dist_cost + time * time_cost

        if layover:
            cost += layover_cost
        return cost

    def _get_shift_cost(self, shift): 
        total_cost = 0
        driver = shift["driver"]
        time_cost = self.instance.get_driver_property(driver, "TimeCost")
        layover_cost = self.instance.get_driver_property(driver, "LayoverCost")

        trailer = shift["trailer"]
        dist_cost = self.instance.get_trailer_property(trailer, "DistanceCost")
        for stop in shift["route"]:
            total_cost += _get_route_cost(shift['route'], time_cost, layover_cost, dist_cost)
        return total_cost

    def get_objective(self):
        return sum(self._get_shift_cost(shift) for shift in self.solution.data.values())


Of course, this can be greatly improved with more tweaks.


No repetition
-----------------

original code:

.. code-block:: python

    data_dict["customers"] = list(data_dict["customers"].values())
    data_dict["trailers"] = list(data_dict["trailers"].values())
    data_dict["drivers"] = list(data_dict["drivers"].values())
    data_dict["sources"] = list(data_dict["sources"].values())

better:

.. code-block:: python

    for key in ["customers","trailers","drivers","sources"]:
        data_dict[key]= list(data_dict[key].values())


Filtering lists or dictionaries
----------------------------------

Filtering lists with list comprehensions is the easiest way to filter one. With pytups, you make it a little shorter.

For example, instead of:

.. code-block:: python

    for r in used_routes.copy():
        if not keep.get(r, False):
            del used_routes[r]

if `used_routes` is a TupList:

.. code-block:: python

    used_routes = used_routes.vfilter(lambda r: keep.get(r, False))

