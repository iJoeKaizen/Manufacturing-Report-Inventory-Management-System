DASHBOARD_MENU = [
    {"name":"My Reports","url":"api/reports/my/","permission":None},
    {"name":"Submit Report","url":"api/reports/create/","permission":None},
    {"name":"All Reports","url":"/reports/","permission":"reports.view_productionreport"},
    {"name":"Approve Reports","url":"/reports/approve/","permission":"reports.can_approve_report"},
    {"name":"Manage Inventory","url":"/inventory/","permission":"inventory.change_inventoryitem"},
    {"name":"Team Performance","url":"/performance/","permission":"core.view_teamperformance"},
    {"name":"User Management","url":"/users/","permission":"accounts.view_user"},
    {"name":"System Dashboard","url":"/admin-dashboard/","permission":None,"superuser_only":True}
]
