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
- RQ09: the demand for each skill should be covered
- RQ10: employee holidays are taken into account. Employees do not work when on holiday.
- RQ11: store holidays are taken into account. Employees do not work on store holidays.
- RQ12: employees can not work during downtime.
- RQ13: employee starting hour preference.
- RQ14: employee max preference hours.
- RQ15: employee weekly schedule
- RQ16: fixed worktable

Parameters
----------

- Contracts: the contracts that the employees have, with the number of days that have to be worked, the weekly hours and the shift.
- Employees: each employee can be a manager or not.
- Shifts: minimum starting hour and maximum ending hour of each shift.
- Demand: the higher the value, the greater the need for employees for each shift (date and hour).
- Employee holidays: the days in which an employee is on holiday and therefore can not work.
- Store holidays: the days in which the store is closed and therefore nobody works.
- Employee downtime: the days in which an employee can not work due an illness.
- Employee preferences: starting and number of hours preferences for one day.
- Weekly schedule: starting and ending hours for each week day.
- Schedule exceptions: starting and ending hours for a specific date.
- Employee schedule: days of the week the employee can work on
- Fixed worktable: worktable fixed by the user

- Parameters:

  - Ending hour: the hour the work center closes.
  - Horizon: the number of weeks that are going to be solved.
  - Minimum resting hours: the minimum amount of hours that have to be rested between the end of the shift on one day, and the start of the shift on the next day.
  - Minimum working hours: the minimum amount of hours that have to be worked each day that the employee works.
  - Slot length: the length of each time slot in minutes.

- Requirements: table indicating which requirements should be complied and which not, and if they are, if they should be applied as strict or soft constraints.

    - rq02: "soft", "strict" or "deactivated for the weekly hours constraint
    - rq03: "soft", "strict" or "deactivated for the maximum daily hours constraint
    - rq05: "soft", "strict" or "deactivated for the maximum days worked per week constraint
    - rq06: "soft", "strict" or "deactivated for the minimum daily hours constraint
    - rq07: "soft", "strict" or "deactivated for the minimum rest hours between shifts constraint
    - rq08: "soft", "strict" or "deactivated for the constraint about needing to have a manager in the store at all times
    - rq09: "soft", "strict" or "deactivated for the skills constraint
    - rq10: "soft", "strict" or "deactivated for the employees' holidays constraint
    - rq11: "strict" or "deactivated for the store holidays constraint
    - rq12: "strict" or "deactivated for the employee downtime constraint
    - rq13: "soft", "strict" or "deactivated for the employee start hour preferences constraint
    - rq14: "soft", "strict" or "deactivated for the employee max preference hours constraint
    - rq15: "soft", "strict" or "deactivated for the employee schedule constraint
    - rq16: "soft", "strict" or "deactivated for the fixed worktable constraint

- Penalties: table indicating for each soft constraint the penalty level when it is not respected.