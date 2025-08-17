# Production Report Entry & Summary System

A professional Django + DRF based system to record, manage, summarize, and analyze **production reports** across multiple manufacturing sections.  
Includes **role-based access control, exportable reports (PDF/Excel), dashboards, and audit trails**.

## Features

### Core
- CRUD for production reports (raw materials, consumables, outputs).
- Filtering & search by date, machine, section, job number.
- Role-based access control with **JWT Authentication**.
- Audit trail for report changes and approvals.
- Soft-delete with admin restore/delete.
- Lock reports after approval to prevent edits.

### Reports
- Compare estimated vs actual usage & output.
- Export individual or bulk reports to **PDF** or **Excel**.
- Track exports in history.

### Summary
- KPIs and dashboards (daily, weekly, monthly, yearly).
- Organized by **Section, Machine, Operator, Job No.**


## Tech Stack

- **Backend**: Django, Django REST Framework
- **Auth**: JWT (SimpleJWT)
- **Database**: PostgreSQL
- **Exports**: WeasyPrint (PDF), OpenPyXL (Excel)
- **Filtering**: django-filter
- **Audit Trail**: custom + django signals


## Project Structure

