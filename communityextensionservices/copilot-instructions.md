1. Scope of the System
   The Centralized Information and Management System for Educational Faculty and Employee Association Membership with Decision Support System (DSS) is designed to organize, manage, and analyze membership information and association activities. The system centralizes records, automates transactions, and provides analytical insights to support effective decision-making for association officers and administrators.

1.1 Functional Scope
B. Membership Information Management
Registration and maintenance of faculty and employee membership records

Member classification (faculty, non-teaching staff, retired, associate)

Membership status tracking (active, inactive, suspended)

Membership history and record updates

C. Association Dues and Contributions Management
Recording of membership dues and contributions

Monitoring of payment schedules and balances

Contribution history per member

Automated reminders for unpaid dues

D. Activity and Program Management
Planning and scheduling of association activities and events

Recording of attendance and participation

E. Document and Record Management
Secure storage of association documents
Archiving of historical records

Controlled access to sensitive documents

F. Centralized Data Repository
Unified database for members, transactions, activities, and documents

G. Decision Support System (DSS)
Membership trend analysis (growth, retention, attrition)

Participation and engagement analysis

Identification of active and inactive members

Decision support recommendations for:

Activity planning
benefit improvements

H. Reporting and Analytics
Automated generation of membership and financial reports

Visual dashboards with charts and summaries

Custom and exportable reports for officers and auditors

I. Notification and Communication
Announcements and system notifications

Payment and membership status alerts

1.2 Non-Functional Scope
Security: Data confidentiality, access control, and audit trails

Performance: Efficient data processing and report generation

Scalability: Supports increasing membership and records

Usability: User-friendly interface for non-technical users

Reliability: Data backup and disaster recovery

Maintainability: Modular design for future enhancements

1.3 Scope Limitations (Out of Scope)
External payroll deduction integration

Online payment gateway processing

Full accounting and financial auditing systems

Integration with external HR or government databases

2. System Flow
   The system flow explains how membership data and transactions are processed and analyzed to support association management and decision-making.

2.1 High-Level System Flow
Users log into the system

Membership and association transactions are processed

Data is stored in a centralized database

DSS analyzes membership and transaction data

Reports and insights are generated

Officers make data-driven decisions

2.2 Detailed System Flow
Step 1: User Authentication
User accesses the system with valid credentials

System verifies role and access permissions

⬇
Step 2: Membership and Transaction Processing
Officers manage member records

Dues and contributions are recorded

Activities and attendance are encoded

⬇
Step 3: Data Storage
All validated data is saved in the centralized database

Member histories and transaction logs are updated

Records are archived securely

⬇
Step 4: Data Pre-Processing
Data validation and cleaning

Member classification and status grouping

Preparation of datasets for DSS analysis

⬇
Step 5: Decision Support Processing
Analysis of membership growth and participation

Evaluation of dues collection efficiency

Identification of trends and patterns

⬇
Step 6: Visualization and Reporting
Dashboards display key performance indicators

Automated and custom reports are generated

Alerts and summaries are presented to officers

⬇
Step 7: Decision-Making and Action
Officers review insights and recommendations

System data supports continuous improvement

3. Simplified System Flow Diagram
   User Login
   ↓
   Membership & Association Transactions
   ↓
   Centralized Database
   ↓
   Data Pre-Processing
   ↓
   Decision Support System
   ↓
   Reports & Dashboards
   ↓
   Association Decision-Making

## NOTES:

- this notes should be used for direction theres no need to strictly comply however scope must not go over it.
- this system will be used as a front for machine learning integration (the system is not the focus) so no need complexity
- The ui should be different from the other systems (this are individual systems under a single project)
- the things should be only used across is authentication and the sidebar (the authentication from the core, sidebar to navigate the system) for reference look for librarymanagement system
- the roles that is must be present are admin , superadmin and user is optional (if the system doesnt need regular user opt it.)
- the admin should be able to access most of the functions while the superadmin is the only role could access the superadmin modules (being able to move to different systems, while admin is restricted to its assigned system)
- use the login page from the core app however change the url for each system (eg: /core/login/ -> /librarymanagement/login/)

## Coding Structure:

### backend

- keep solid coding paradigm for easier debugging
  - services.py -> business logics (like queries)
  - utils.py -> utility logics
  - views.py -> the api endpoints
- ensure all urls are properly connected and configured to the frontend
- (optional) if the function reach a certain complexity , if necessary create a simple test
- do not implement the machine learning but create a space for future (the ml is not the scope only system)
- the backend should still use actual models and queries better demonstrate ML models for authenticity
- the models, forms, logics should be updated to accommodate the scope and the future ml integration (eg: adding fields for ml predictions)
- use seed for the initial data population to better demonstrate the system and ml integration (refer to informationmanagement for reference)
- use the same login however change the url for each system (eg: /core/login/ -> /ces/login/)

## optional

- if the system has users strictly manage the user access to user level only, no sensitive mutations

### frontend

```
<style></style>
<script></script>
```

- inline page style is acceptable - no need another css file same with javascript
- bootstrap is allowed if it will make it faster to develop
- as possible avoid using symbols and use proper svg icons
- keep the ui modern look
- prioritize django templates of api call over ajax unless the benefit is more.
- different styles of navigation is allowed as long as the superadmin modules and logout button is present (refer to librarymanagement system sidebar)
- keep the machine learning ui part even if there is no backend
