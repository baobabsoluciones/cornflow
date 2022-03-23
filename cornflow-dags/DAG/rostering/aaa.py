import datetime
import random

initial_date = datetime.date(2021, 9, 6)
initial_hour = 7
end_hour = 20
horizon = 4
dates = [initial_date + datetime.timedelta(days=i) for i in range(0, horizon * 7)]
initial_demand = 20
increase = True

demand = []

for date in dates:
    current_demand = initial_demand
    increase = True
    for hour in range(initial_hour, end_hour + 1):
        demand.append(
            {"day": date.strftime("%Y-%m-%d"), "hour": hour, "demand": current_demand}
        )
        if increase and hour > 14:
            if random.uniform(0, 1) >= 0.5:
                increase = False
        elif increase and hour > 16:
            if random.uniform(0, 1) >= 0.2:
                increase = True

        modify = random.uniform(0, 1)

        if increase and modify >= 0.4:
            current_demand = current_demand + 10
        elif not increase and modify >= 0.4:
            current_demand = current_demand - 10
        else:
            current_demand = current_demand

        if current_demand < 5:
            current_demand = 1

print(demand)
