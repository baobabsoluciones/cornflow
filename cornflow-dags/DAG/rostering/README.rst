Problem
-------

A set of employees have to work a given amount of hours or days per week, and we have to find the assignment of employees to timeslots

Decision
--------

For each employee and time slot if the employee works said time slot or not.

This decision is subject to:

- RQ01: at least one employee is at the work center at all times.
- RQ02: employees work their weekly hours.
- RQ03: employees can not work more than a given amount of hours every day.
- RQ04: each employee only has one shift on one day.
- RQ05: employees can not exceed their working days per week.
- RQ06: employees at least work the minimum amount of hours every day.
- RQ07: employees rest the minimum amount of hours between working days.
- RQ08: at least one manager is at the work center at all times.

Parameters
----------

- Contracts: the contracts that the employees have, with the number of days that have to be worked, the weekly hours and the shift.
- Employees: each employee can be a manager or not.
- Shifts: minimum starting hour and maximum ending hour of each shift.
- Parameters:

  - Ending hour: the hour the work center closes.
  - Horizon: the number of weeks that are going to be solved.
  - Minimum resting hours: the minimum amount of hours that have to be rested between the end of the shift on one day, and the start of the shift on the next day. 
  - Minimum working hours: the minimum amount of hours that have to be worked each day that the employee works. 
  - Opening days: the number of days that the work center opens, the first day is always considered to be a Monday.
  - Slot length: the length of each time slot in minutes.
  - Starting date: the first day that has to be solved.
  - Starting hour: the hour the work center opens. 