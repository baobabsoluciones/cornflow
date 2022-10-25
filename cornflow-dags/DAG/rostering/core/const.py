INSTANCE_KEYS_RELATION = {
    ("employees", "id"): [
        ("contracts", "id_employee"),
        ("skills_employees", "id_employee"),
    ],
    ("shifts", "id"): [("contracts", "id_shift")],
    ("skills", "id"): [
        ("skills_employees", "id_skill"),
        ("skill_demand", "id_skill"),
    ],
}
