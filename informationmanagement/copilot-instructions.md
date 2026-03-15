1. Scope of the System
   The Management Information System for the Community Extension Services Office and Linkages Offices with Data Analytics is designed to centralize information, streamline operations, and support data-driven decision-making for community extension programs and institutional linkages. The system manages projects, partners, beneficiaries, and activities while providing analytical insights to improve planning, implementation, and evaluation.

1.1 Functional Scope

B. Community Extension Project Management
Registration and management of extension projects and programs

Project categorization (education, health, livelihood, environment, etc.)

Scheduling of activities and timelines

Project status tracking (proposed, ongoing, completed)

C. Beneficiary Management
Registration of partner communities and beneficiaries

Beneficiary profiling and classification

D. Linkages and Partnership Management
Partner activity involvement and contribution records

Partnership status monitoring

E. Activity and Event Management
Scheduling and monitoring of extension activities and outreach programs

Attendance and participation recording

Documentation uploads (photos, reports, accomplishment reports)

F. Centralized Data Repository
Unified database for projects, beneficiaries, partners, activities, and documents

Secure document storage and archiving

Data validation and consistency checking

G. Data Analytics Module
Analysis of extension program reach and coverage

Trend analysis of extension programs by type and location

Outcome and impact indicators generation

H. Reporting and Decision Support
Automated generation of accomplishment and impact reports

Visual dashboards for management and accreditation use

Custom report generation for institutional and regulatory requirements

Data-driven recommendations for program improvement and expansion

I. Notification and Communication
Activity schedules and deadline notifications

Partner and beneficiary announcements

1.2 Non-Functional Scope
Security: Role-based access, data privacy, and audit trails

Performance: Efficient processing of transactions and analytics

Scalability: Supports increasing projects, beneficiaries, and partners

Usability: User-friendly interface for non-technical users

Reliability: Data backup and recovery mechanisms

Maintainability: Modular system architecture for future upgrades

1.3 Scope Limitations(Out of Scope)
Financial accounting and fund disbursement systems

Full geographic information system (GIS) integration

Real-time mobile tracking of field activities

Integration with external government databases

2. System Flow
   The system flow illustrates how data flows through the system from data entry to analytics and decision support.

2.1 High-Level System Flow
Users log into the system

Extension and linkage transactions are performed

Data is stored in a centralized database

Data analytics processes historical and current data

Reports and insights are generated

Management uses analytics for decision-making

2.2 Detailed System Flow
Step 1: User Authentication
Users access the system using valid credentials

System verifies roles and access permissions

⬇
Step 2: Data Entry and Transaction Processing
Extension coordinators manage projects and activities

Linkages officers manage partner records and agreements

Faculty and staff encode participation and reports

⬇
Step 3: Data Storage
Project, partner, and beneficiary data are saved in the centralized database

Activity logs and documents are archived securely

⬇
Step 4: Data Preprocessing
Data validation and cleaning

Categorization of projects, partners, and beneficiaries

Preparation of datasets for analytics

⬇
Step 5: Data Analytics Processing
Analysis of participation and coverage

Partner engagement and performance analysis

Trend and outcome analysis of extension programs

⬇
Step 6: Visualization and Reporting
Dashboards display key performance indicators

Automated accomplishment and impact reports are generated

Alerts highlight gaps or areas for improvement

⬇
Step 7: Decision Support and Improvement
Management reviews analytical insights

Decisions are made on program enhancement, expansion, or partnerships

Continuous improvement is supported through updated data

3. Simplified System Flow Diagram
   User Login
   ↓
   Extension & Linkages Transactions
   ↓
   Centralized Database
   ↓
   Data Preprocessing
   ↓
   Data Analytics Engine
   ↓
   Reports & Dashboards
   ↓
   Management Decision-Making

## NOTES:

- this notes should be used for direction theres no need to strictly comply however scope must not go over it.
- this system will be used as a front for machine learning integration (the system is not the focus) so no need complexity
- The ui should be different from the other systems (this are individual systems under a single project)
- the things should be only used across is authentication and the sidebar (the authentication from the core, sidebar to navigate the system ) for reference look for librarymanagement system
- the roles that is must be present are admin , superadmin and user is optional (if the system doesnt need regular user opt it.)
- the admin should be able to access most of the functions while the superadmin is the only role could access the superadmin modules (being able to move to different systems, while admin is restricted to its assigned system)

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
- use the same login however change the url for each system (eg: /core/login/ -> /ims/login/)

### optional

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
