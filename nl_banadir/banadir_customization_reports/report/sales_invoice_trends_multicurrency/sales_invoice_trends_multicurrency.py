from nl_banadir.banadir_customization_reports.controllers.trends import (
    get_columns,
    get_data,
)


def execute(filters=None):
    if not filters:
        filters = {}
    data = []
    conditions = get_columns(filters, "Sales Invoice")
    data = get_data(filters, conditions)

    print("DATA", data)

    return conditions["columns"], data
