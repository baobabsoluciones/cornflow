INSTANCE_KEYS_RELATION = {
    ("employees", "id"): [
        ("contracts", "employee_id"),
        ("skills_employee", "id_employee"),
    ],
    ("shifts", "id"): [("contracts", "id_shift")],
    ("skills", "id"): [
        ("skills_employees", "id_skill"),
        ("skill_demand", "id_skill"),
    ],
}
