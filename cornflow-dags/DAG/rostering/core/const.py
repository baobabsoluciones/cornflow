INSTANCE_KEYS_RELATION = {
    ("employees", "id"): [
        ("contracts", "id_employee", True),
        ("skills_employees", "id_employee", False),
        ("employee_holidays", "id_employee", False),
        ("employee_downtime", "id_employee", False),
        ("employee_preferences", "id_employee", False),
        ("employee_schedule", "id_employee", False),
    ],
    ("shifts", "id"): [("contracts", "id_shift", False)],
    ("skills", "id"): [
        ("skills_employees", "id_skill", False),
        ("skill_demand", "id_skill", False),
    ],
}
