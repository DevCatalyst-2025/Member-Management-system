⚡ DevCatalyst Portal: A Multi-Role Task Management System
DevCatalyst is a comprehensive, multi-role web application built with Streamlit and Supabase. It serves as a centralized portal for managing tasks, resolving doubts, and tracking progress within a team or organization. The application is designed with a clear separation of roles: Members, Representatives, and an Admin, each with a tailored interface and specific permissions.

✨ Key Features
The portal provides distinct functionalities based on user roles:

👤 Member Features

Dashboard: An at-a-glance overview of personal progress, including metrics for total tasks, completed tasks, pending tasks, and accumulated points.

Task Management: View a detailed list of assigned tasks with sorting (by due date, priority, etc.) and filtering (by status) capabilities.

Task Submission: A simple interface to submit completed tasks by providing a link and optional notes.

Help & Resources: A dedicated page to submit doubts or resource requests to Representatives and view their replies in a threaded conversation format.

🧑‍💼 Representative Features

Task Assignment: A form to create and assign new tasks to members, specifying title, description, priority, points, and due date.

Submission Verification: A queue of submitted tasks awaiting review. Representatives can view submission details and mark tasks as 'Completed'.

Doubt Resolution: A centralized view of all member doubts. Representatives can post replies and mark doubts as 'Resolved' once addressed.

👑 Admin Features

Analytics Dashboard: A high-level view of the entire system with visualizations for:

Task status distribution.

Tasks assigned per member.

Priority distribution.

Doubt resolution rates.

Data Management:

Export: Download tasks and doubts data as CSV files for external analysis or reporting.

Raw Data View: Inspect the raw data for tasks, doubts, and the entire application state directly in the UI.

Data Cleanup: Secure, two-step confirmation actions to clear all tasks, doubts, or completely reset the application data.

🛠️ Tech Stack
Frontend: Streamlit

Backend & Database: Supabase (PostgreSQL)

Data Manipulation: Pandas

Deployment: Streamlit Community Cloud (or any other compatible service)



## License
The content of this repository is licensed under the 
[Creative Commons Attribution-NoDerivatives 4.0 International License (CC BY-ND 4.0)](https://creativecommons.org/licenses/by-nd/4.0/).

[![License: CC BY-ND 4.0](https://licensebuttons.net/l/by-nd/4.0/88x31.png)](https://creativecommons.org/licenses/by-nd/4.0/)
