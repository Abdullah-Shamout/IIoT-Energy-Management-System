# Industrial IoT Energy Management System

## Project Overview

This project develops an intelligent Industrial IoT (IIoT) Energy Management System designed to maintain energy consumption in industrial environments over a period of time. Leveraging real-time data from IoT devices, an AI-powered agent provides energy optimization plans, budget monitoring, and device control through a natural language chatbot interface and a comprehensive dashboard.



## Key Features

- **Real-time Energy Monitoring:** Collects and visualizes energy consumption data from IoT devices (Motor, Fan, Light Bulb) in 15-second intervals.
- **AI-Powered Optimization:** An intelligent agent (GPT-4) generates energy-saving schedules based on real-time data and predefined budgets.
- **Three-Path For Schedule Approval System:** Operators can choose to:
    - **Apply Now:** Execute all actions in the plan immediately.
    - **Apply Scheduled:** Schedule each action to run at its planned time (Kuwait time, one-time execution for today), with automatic revert to previous state after the action window.
    - **Modify:** Customize the plan by changing parameters or deleting specific actions by number before approval.
- **Energy Budgeting & Alerts:** Monitors total energy consumption against a user-defined budget (in kWh) and triggers alerts when the budget is exceeded.
- **Natural Language Chatbot:** Interact with the system using natural language to query device status, consumption, budget, generate reports, and control devices.
- **MCP Device Control:** Utilizes the Model Context Protocol (MCP) for secure and validated actuation of IoT devices.
- **Interactive Dashboard:** Provides a real-time overview of device statuses, energy consumption, budget comparison, and efficiency scores.
- **Dark/Light Mode:** User-friendly interface with toggleable theme.

## Use Case

Our system can be used to monitor industrial factories energy consumption. The operator sets an energy budget and when the overall energy consumption of the factory exceeds the energy budget the Ai suggests optimization schedule that aims to reduce the energy consumption.
Such schedule can be (This is just the actions part of the schedule. The schedule consists of other parts such as, predefined budget vs overall energy consumption comparison, discription of every device consumption, etc... These parts are well formated for better user experience):
1- reduce motor intensity to 60% from 6:00pm to 10:pm.
2- turn off the light bulb from 8:00pm to 10:pm.
3- turn off the fan from 1:00am to 3:00am.

## User Interface

The application features a modern, responsive user interface with both light and dark mode support.

| Dashboard (Light Mode) | Dashboard (Dark Mode) |
| :---: | :---: |
| ![Dashboard Overview](screenshots/ui%201.png) ![Chatbot Interaction](screenshots/ui%202.png) | ![Dashboard Dark](screenshots/ui%204.png) ![Energy Charts](screenshots/ui%205.png) |

| Chatbot Interface (Light Mode) | Chatbot Interface (Dark Mode)|
| :---: | :---: |
|![Dashboard Light](screenshots/ui%203.png)  | ![Chatbot UI](screenshots/ui%206.png) |

## System Architecture

The system is composed of a backend running on a Raspberry Pi and a frontend accessible via a web browser on a laptop or desktop.

### Backend (Raspberry Pi)
- **Database:** TimescaleDB (PostgreSQL with time-series extensions) for storing sensor readings and system configurations.
- **API:** Flask-based REST API for data retrieval, device control, and AI agent communication.
- **AI Agent:** GPT-4 integration for natural language understanding, optimization plan generation, and report generation.
- **MCP Server:** Manages communication with IoT devices and executes commands.
- **Data Aggregators & Budget Alerts:** Python services for collecting data, calculating consumption, and monitoring budget.

### Frontend (Web Browser)
- **Framework:** React 18 with Vite for fast development.
- **Styling:** Tailwind CSS for a responsive and modern UI.
- **Charting:** Recharts library for interactive data visualizations (line graphs, pie charts).
- **Communication:** Axios for API calls to the Flask backend.

## Setup and Installation

### Prerequisites

- **Raspberry Pi:** Running Ubuntu 22.04 (or similar Debian-based OS).
- **Node.js & pnpm:** For frontend development (on your laptop).
- **Python 3.11 & pip:** For backend services.
- **TimescaleDB:** Installed and configured on the Raspberry Pi.

### 1. Backend Setup (on Raspberry Pi)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Database Configuration:**
    - Ensure TimescaleDB is running.
    - Create your database and user.
    - Apply the schema:
      ```bash
      psql -h localhost -U <your_db_user> -d <your_db_name> -f schema.sql
      ```

4.  **Environment Variables:**
    - Create a `.env` file in the backend root directory.
    - Add your OpenAI API key and database connection details:
      ```
      OPENAI_API_KEY=your_openai_api_key
      DATABASE_URL=postgresql://user:password@localhost:5432/dbname
      ```

5.  **Run Backend Services:**
    ```bash
    ./start_all.sh
    ```
    This script will start `app.py`, `mcp_server.py`, `data_aggregator.py`, and `budget_alert.py`.

### 2. Frontend Setup (on your Laptop)

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install Node.js dependencies:**
    ```bash
    pnpm install
    ```

3.  **Configure API Endpoint:**
    - Open `src/services/api.ts`.
    - Change `baseURL` to your Raspberry Pi's IP address:
      ```typescript
      const api = axios.create({
        baseURL: 'http://<raspberry-pi-ip>:5000',
        timeout: 180000,
      });
      ```

4.  **Start Frontend Development Server:**
    ```bash
    pnpm dev
    ```
    The application will be available at `http://localhost:5173` (or similar).

## Team Members

- Abdullah Shamout
- Sulaiman Alrefai
- Tarek Adi
- Ahmed Osman

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
