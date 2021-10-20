Coding style and rules
============================

The following rules and notation come from examples in PR-revisions that we think can become common rules. Each rule will have an example and a description.


Commenting out code
-------------------------

Having commented code makes no sense. It should be eliminated from the commit altogether. If for some reason you fear losing the piece of code in the future, remember that it will be present in the git history (if it has taken part of the master branch at some point):

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

In the example, we're checking for the existance of instance and solution when creating a new Experiment.

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
