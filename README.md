# Firebase Vite Template with MUI Theme

A modern, production-ready template for quickly building Firebase applications with React, Vite, Material UI, Tailwind CSS v4, and ECharts.

## Project Overview
This project is the Outstaffer Business Metrics Dashboard, a comprehensive internal tool designed to provide real-time insights into key performance indicators (KPIs) across various aspects of the business. It centralizes data related to revenue, customer acquisition, geographical distribution, health insurance metrics, and product add-ons, enabling data-driven decision-making and strategic planning.

The main goals of this dashboard are:
- To offer a clear and consolidated view of company performance.
- To identify trends, opportunities, and potential challenges quickly.
- To support different departments with tailored data visualizations.
- To improve operational efficiency by providing easy access to critical metrics.

This document serves as a guide for developers and stakeholders to understand, operate, maintain, and extend the dashboard.

## High-Level Architecture
The system is composed of the following main components:
- **Frontend:** React (with Vite, Material UI, Tailwind CSS, ECharts)
- **Backend:** FastAPI (Python)
- **Database:** Google BigQuery
- **Data Processing Scripts:** Python scripts in the `python/` directory.

The React frontend, built with Vite and styled using Material UI and Tailwind CSS, provides the user interface and visualizations (using ECharts). It communicates with the FastAPI backend via REST APIs to fetch data. The FastAPI backend serves data queried from Google BigQuery. Data in BigQuery is periodically updated and aggregated by Python scripts located in the `python/` directory, which process raw data or data from other sources and store it in a format suitable for dashboard display.

## Prerequisites
Before you begin, ensure you have the following tools and accounts set up:
- **Python:** Version 3.8 or newer.
- **Node.js:** Version 18 or newer (for frontend development).
- **`gcloud` CLI (Google Cloud SDK):** Installed, configured, and authenticated with access to the project's BigQuery.
- **Firebase CLI:** Installed and authenticated, for frontend deployment and local Firebase services emulation.
- **IDE/Text Editor:** A suitable code editor such as VS Code.
- **Google Cloud Platform Access:** Access to the company's Google Cloud Platform project (specifically for BigQuery).
- **Firebase Project Access:** Access to the company's Firebase project.

## Setup and Local Development

This section guides you through setting up the project for local development.

### 1. General Setup

**Clone the Repository:**
```bash
git clone <repository-url>
cd <repository-directory>
```
Replace `<repository-url>` with the actual URL of this repository and `<repository-directory>` with the name of the directory created.

**Environment Variables:**
Sensitive information such as API keys, database credentials, and project IDs should be managed using environment variables and **not** hardcoded into the source code.

*   **Suggestion:** Create a `.env` file in the project root, or within specific directories like `backend/` and `python/` for managing these variables. Load these into your shell environment before running the applications. The method for setting environment variables depends on your operating system (e.g., using `export VAR_NAME=value` on Linux/macOS or `set VAR_NAME=value` then `setx VAR_NAME "%VAR_NAME%"` on Windows).
*   **Key Environment Variables:**
    *   `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google Cloud service account key JSON file. This is used by `gcloud` and Python client libraries if you are authenticating using a service account. Alternatively, ensure you have run `gcloud auth application-default login` for user-based authentication.
    *   `BIGQUERY_PROJECT_ID`: Your Google Cloud Project ID where BigQuery datasets are stored.
    *   `API_KEY`: Any specific API keys required for the backend services (if applicable).
    *   `FIREBASE_CONFIG_xxx`: Firebase related API keys and IDs for the frontend will be configured in `src/firebase.js` (see Frontend Setup).

### 2. Backend Setup (`backend/` directory)

The backend is a FastAPI application.

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```
2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the FastAPI development server:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8080 --reload
    ```
    The backend will typically be available at `http://localhost:8080`.

### 3. Frontend Setup (Project Root Directory)

The frontend is a React application built with Vite.

1.  **Navigate to the project root directory** (if you are in `backend/` or `python/`):
    ```bash
    cd ..
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Run the Vite development server:**
    ```bash
    npm run dev
    ```
    The frontend will typically be available at `http://localhost:5173` (or another port if 5173 is busy, Vite will indicate this).
4.  **Firebase Configuration:**
    Update your Firebase project details in `src/firebase.js`. Refer to the "Firebase Setup" section below for details on creating and configuring your Firebase project.

### 4. Python Data Scripts Setup (`python/` directory)

These scripts are used for data processing and populating BigQuery.

1.  **Navigate to the Python scripts directory:**
    ```bash
    cd python
    ```
    (If you are at the root, otherwise adjust path accordingly e.g., `cd ../python` if in `backend`)
2.  **Virtual Environment:**
    These scripts can use the same virtual environment created for the backend (`../backend/venv`) if their dependencies are compatible. Activate it if not already active:
    ```bash
    source ../backend/venv/bin/activate # Adjust path if necessary
    ```
    If they have conflicting dependencies, create a separate virtual environment in the `python/` directory following the same steps as for the backend.
3.  **Install Dependencies:**
    If there's a `requirements.txt` in the `python/` directory:
    ```bash
    pip install -r requirements.txt
    ```
    Ensure any packages used by the scripts (e.g., `google-cloud-bigquery`) are installed.
4.  **Environment Variables:**
    Ensure that the necessary environment variables for Google Cloud access (e.g., `GOOGLE_APPLICATION_CREDENTIALS` or having `gcloud` auth configured, and `BIGQUERY_PROJECT_ID`) are available in the shell environment where you execute these scripts.

## Running Python Data Scripts

The Python scripts located in the `python/` directory are responsible for collecting, processing, and snapshotting data into Google BigQuery tables. This data is then consumed by the backend API to populate the dashboards.

**Prerequisites:**
- Ensure you have activated the appropriate Python virtual environment (see "Python Data Scripts Setup" under "Setup and Local Development").
- Ensure all necessary environment variables (e.g., `BIGQUERY_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud` user authentication) are correctly set in your terminal session.

**General Usage:**
To run a script, navigate to the project root directory and use the following format:
```bash
python python/script_name.py [arguments]
```
Replace `script_name.py` with the actual name of the script you intend to run.

**Example Script:**
For instance, to run the script that snapshots revenue metrics, you might use:
```bash
python python/snapshot-revenue-metrics.py
```

**Common Arguments:**
Many scripts support command-line arguments for customized behavior. A common and important one is `--dry-run`:
-   `--dry-run`: This argument allows the script to perform all its operations, such as fetching and processing data, but it will not write any data to BigQuery or make other persistent changes. It's highly recommended to use this flag to validate a script's behavior before running it in normal mode.

    Example:
    ```bash
    python python/snapshot-revenue-metrics.py --dry-run
    ```

Always check a script's specific documentation or use an argument like `--help` (if implemented by the script) to see all available options.

## Backend API Overview

The backend is a FastAPI application, with `backend/main.py` serving as the main entry point. It primarily serves data queried from Google BigQuery to the frontend.

**API Modules (Routers):**
The API functionality is organized into modules within the `backend/routers/` directory:
-   `revenue.py`: Endpoints for accessing various revenue-related metrics, including current MRR, trends, and breakdowns.
-   `addons.py`: Endpoints related to product add-on metrics, such as usage and revenue from add-ons.
-   `health_insurance.py`: Endpoints for data and metrics concerning health insurance products or plans.
-   `customers.py`: Endpoints providing access to customer-related data, potentially including demographics, acquisition metrics, or segmentation.
-   `geography.py`: Endpoints for geographical data, such as customer distribution or revenue by region.

**Authentication:**
The API uses API key-based authentication to protect its endpoints. Clients must include a valid API key in the `X-API-Key` header of their requests.
```
X-API-Key: YOUR_API_KEY
```
The `API_KEY` should be set as an environment variable for the backend application (refer to the "Environment Variables" subsection under "Setup and Local Development"). The authentication logic can be reviewed in `backend/auth.py`.

## Frontend Overview

The frontend is a React application, built using Vite for a fast development experience. It provides interactive dashboards to visualize business metrics.

**Main Application Component and Routing:**
-   `src/App.jsx`: This is the main application component where routing is defined using `react-router-dom`. It sets up the overall structure, theme provider, and authentication context.
-   `src/components/auth/ProtectedRoute.jsx`: Ensures that dashboard routes are accessible only to authenticated users.

**Available Dashboards:**
The primary user interface consists of several specialized dashboards, components for which are typically located in `src/components/`:
-   `src/components/Dashboard.jsx`: Serves as a central or main dashboard, potentially aggregating key metrics or providing navigation to other specialized dashboards.
-   `src/components/RevenueDashboard.jsx`: Displays revenue-specific metrics, trends, and breakdowns.
-   `src/components/AddonsDashboard.jsx`: Focuses on metrics related to product add-ons.
-   `src/components/HealthInsuranceDashboard.jsx`: Presents data concerning health insurance plans and metrics.
-   `src/components/CustomerDashboard.jsx`: Shows customer-related data, such as segmentation, acquisition, and value metrics.
-   `src/components/GeographicDashboard.jsx`: Visualizes data based on geographical distribution.

**Data Fetching:**
-   Data for the dashboards is primarily fetched from the backend API.
-   `src/services/ApiService.js`: This service contains helper functions that handle the communication with the backend REST API endpoints. It encapsulates the logic for making requests (including authentication with the API key) and processing responses. It also includes fallback mechanisms for development when the API is unavailable.

**UI Technologies:**
-   **Material UI (MUI):** Used as the core component library, providing a wide range of pre-built and customizable UI elements.
    -   Theme Customization: The MUI theme can be customized in `src/theme.js`, allowing for consistent styling across the application (colors, typography, component variants, etc.).
-   **Tailwind CSS:** Employed for utility-first CSS styling, offering flexibility for custom styling needs alongside MUI.
-   **ECharts:** Integrated for rendering various charts and data visualizations within the dashboards. The `src/components/Chart.jsx` component is a wrapper for using ECharts.

## Database

The primary database supporting this application—for both the backend API and the Python data processing scripts—is **Google BigQuery**.

**Connection and Authentication:**
-   Connections to BigQuery are typically managed using the Google Cloud client libraries for Python (e.g., `google-cloud-bigquery`).
-   Authentication relies on Application Default Credentials (ADC). Developers need to ensure their environment is authenticated:
    -   By running `gcloud auth application-default login`.
    -   Or, by setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of a service account JSON key file.
-   The `BIGQUERY_PROJECT_ID` environment variable should also be set to your Google Cloud Project ID where the BigQuery datasets reside. (Refer to the "Environment Variables" section under "Setup and Local Development").

**SQL Queries:**
-   The `sql-queries/` directory contains examples of SQL queries. These may include queries used by the Python snapshot scripts for data transformation and aggregation, or queries used for generating specific metrics for the dashboards. For example, `sql-queries/dashboard_metrics.monthly_contract_metrics.sql` provides a reference for contract metric calculations.

**Data Population:**
-   The Python scripts located in the `python/` directory are responsible for populating and periodically updating the tables in BigQuery. The backend API then queries these tables to serve data to the frontend dashboards.

## Extending Functionality

This section provides guidance on how to add new features to the dashboard system, such as new dashboards or data processing scripts.

### 1. Adding a New Dashboard

Adding a new dashboard involves steps in both the backend and frontend.

**Backend Steps:**

1.  **Define Data Requirements:**
    *   Clearly define what new information or metrics the dashboard will display.
    *   Determine if the required data can be derived from existing BigQuery tables or if new data processing is needed.

2.  **Data Processing (if new data/aggregation is needed):**
    *   **Modify or Create Python Scripts:**
        *   Assess if existing Python snapshot scripts in the `python/` directory (e.g., `snapshot-revenue-metrics.py`) can be updated to generate the new data.
        *   If the logic is substantially new, create a new Python script in the `python/` directory.
    *   **Design BigQuery Tables/Views:**
        *   If new tables or views are required in BigQuery to store the processed data, design their schema.
    *   **Write SQL Queries:**
        *   Develop any necessary SQL queries for data transformation or aggregation. Consider storing complex or reusable queries in the `sql-queries/` directory.

3.  **Create a New API Router:**
    *   Add a new Python file in `backend/routers/` (e.g., `new_dashboard_router.py`).
    *   Inside this file, define a FastAPI `APIRouter`.
    *   Implement endpoints on this router that will query the relevant BigQuery tables/views to fetch data for the new dashboard. Ensure endpoints are protected by API key authentication (see `backend/auth.py` and existing routers for examples).

4.  **Register the New Router:**
    *   In `backend/main.py`, import the newly created router.
    *   Include it in the FastAPI application using `app.include_router(new_dashboard_router.router, prefix="/api/v1/new_dashboard", tags=["New Dashboard"])` (adjust prefix and tags as needed).

**Frontend Steps:**

1.  **Create New React Components:**
    *   Develop a new main React component for the dashboard (e.g., `src/components/NewDashboard.jsx`).
    *   Create any necessary sub-components, such as specific charts or data display elements. You can reuse or adapt `src/components/Chart.jsx` for ECharts visualizations.

2.  **Fetch Data from Backend:**
    *   Add new asynchronous functions to `src/services/ApiService.js`. These functions will call the new backend API endpoints created in the previous steps.
    *   Ensure these functions handle API responses and errors appropriately.

3.  **Define Routing:**
    *   In `src/App.jsx` (or your dedicated routing configuration file if you have one), add a new `Route` within the `<Routes>` component. This route should map a URL path to your new dashboard component (e.g., `<Route path="/new-dashboard" element={<ProtectedRoute><NewDashboard /></ProtectedRoute>} />`).

4.  **Update Navigation:**
    *   If you have a sidebar, top navigation bar, or other navigation elements, update them to include a link to the new dashboard. This might involve modifying components like `src/components/Dashboard.jsx` or a dedicated navigation component.

### 2. Adding a New Python Data Script (Snapshot Script)

New Python scripts might be needed to process new data sources, perform different types of aggregations, or populate new tables in BigQuery for new dashboards or features.

1.  **Purpose:**
    *   Clearly define the objective of the new script. What data will it process? What tables will it create or update in BigQuery?

2.  **Location:**
    *   Place new Python data processing scripts in the `python/` directory.

3.  **Structure and Best Practices:**
    *   **Follow Existing Patterns:** Model your new script on existing ones like `python/snapshot-revenue-metrics.py` for consistency.
    *   **Utilize Utilities:**
        *   `python/metrics_utils.py`: Contains functions for fetching and processing common data entities from BigQuery (e.g., contracts, companies, fees). Leverage these to avoid redundant code.
        *   `python/snapshot_utils.py`: Provides the `write_snapshot_to_bigquery` function for reliably writing pandas DataFrames to BigQuery, including schema handling, dry-run capabilities, and backup/overwrite logic. Use this for your BigQuery write operations.
    *   **Argument Parsing:** Implement command-line argument parsing using `argparse`. Include common arguments like `--date` (for backfilling specific dates), `--dry-run` (to validate logic without writing to BigQuery), and `--help`.
    *   **Logging:** Implement comprehensive logging using the `logging` module throughout your script to track its execution and help with debugging.
    *   **Configuration:**
        *   Ensure the script can access necessary configurations such as the BigQuery Project ID, dataset names, and target table names. This is typically managed via environment variables (e.g., `BIGQUERY_PROJECT_ID`) or constants defined within the script or a shared configuration module.
        *   The target table ID for `write_snapshot_to_bigquery` should be in the format `your-project-id.your_dataset_id.your_table_name`.

4.  **Scheduling:**
    *   Once a script is developed and tested, it will need to be scheduled to run periodically (e.g., daily, weekly, monthly) to keep the BigQuery data up-to-date.
    *   Scheduling is an external concern and is not managed by the application codebase itself. Common methods for scheduling Python scripts include:
        *   **Cron jobs:** On a Linux server.
        *   **Google Cloud Scheduler:** A fully managed cron job service on GCP, which can trigger Cloud Functions, Pub/Sub messages, or HTTP endpoints.
        *   **CI/CD Pipelines:** Systems like GitHub Actions or GitLab CI can be configured to run scripts on a schedule.
        *   **Orchestration Tools:** For more complex workflows, tools like Apache Airflow or Prefect can be used.

## Features

- 🔥 **Firebase Integration** - Authentication, Storage, and optional Firestore
- 🚀 **Vite** - Lightning fast builds and HMR
- 🎨 **Material UI Theme** - Customized MUI theme for consistent styling
- 💅 **Tailwind CSS v4** - Utility classes for additional styling flexibility
- 📊 **ECharts** - Powerful charting library with geographic map support
- 🔒 **Authentication** - Email/password and Google sign-in with protected routes
- 📱 **Responsive Design** - Mobile-friendly interface using MUI and Tailwind
- 🧩 **Component Structure** - Organized component architecture
- 🎭 **Custom Theme** - Pre-configured MUI theme with consistent styling

## Technologies

| Category           | Technology                                  |
|--------------------|---------------------------------------------|
| Framework          | React 19                                    |
| Build Tool         | Vite 6.2+                                   |
| UI Library         | Material UI 5.15+                           |
| CSS Framework      | Tailwind CSS v4                             |
| Authentication     | Firebase Authentication                      |
| Database (Optional)| Firestore                                   |
| File Storage       | Firebase Storage                            |
| Routing            | React Router v7                             |
| Charts             | ECharts                                     |

## Project Structure

```
project-root/
├── src/
│   ├── components/
│   │   ├── auth/
│   │   │   ├── AuthContainer.jsx   # Auth wrapper component
│   │   │   ├── LoginComponent.jsx  # Login form
│   │   │   ├── RegisterComponent.jsx # Registration form
│   │   │   └── ProtectedRoute.jsx  # Route protection component
│   │   ├── common/
│   │   │   └── LinkBehaviour.jsx   # Custom link for MUI integration
│   │   ├── Chart.jsx               # ECharts component
│   │   └── Dashboard.jsx           # Main app dashboard
│   ├── contexts/
│   │   └── AuthContext.jsx         # Authentication context
│   ├── services/
│   │   └── authService.js          # Auth helper functions
│   ├── App.jsx                     # Main application component
│   ├── main.jsx                    # Application entry point
│   ├── firebase.js                 # Firebase configuration
│   ├── theme.js                    # MUI theme configuration
│   └── index.css                   # Global styles with Tailwind
├── public/
│   └── favicon.ico                 # App favicon
├── index.html                      # HTML template
├── package.json                    # Dependencies and scripts
├── tailwind.config.js              # Tailwind configuration
├── vite.config.js                  # Vite configuration
├── firebase.json                   # Firebase configuration
└── .firebaserc                     # Firebase project settings
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint to check code

## Customization

### Theme Customization

You can customize the theme by modifying `src/theme.js`. The theme is built on Material UI's theming system, allowing you to:

- Change color palettes
- Adjust typography settings
- Modify component styles
- Update spacing and sizing

### Styling Approach

This template uses a hybrid approach to styling:

1. **MUI Components**: Styled through the theme system
2. **Tailwind CSS**: For utility-based styling needs
3. **CSS Modules**: Available for component-specific styles

### Authentication

The template includes both email/password and Google authentication. To customize:
- Edit `src/components/auth/` components
- Modify `src/services/authService.js` to add or remove auth providers

### Charts

ECharts is included for data visualization. Example usage is in `src/components/Chart.jsx`.
- Geographic maps support is available for visualizing global data
- Customize chart options in the Chart component

## Deployment

1. Install Firebase CLI: `npm install -g firebase-tools`
2. Login to Firebase: `firebase login`
3. Initialize Firebase: `firebase init` (select Hosting)
4. Build the project: `npm run build`
5. Deploy to Firebase: `firebase deploy`

## Security Considerations

- Always implement proper security rules in Firebase
- For Firestore, use rules based on user authentication
- For Storage, restrict access to authenticated users
- Consider adding Firebase Functions for server-side logic

## License

This template is MIT licensed.bash
npm install
   ```
3. Update Firebase configuration in `src/firebase.js` with your Firebase project details
4. Start the development server:
   ```bash
   npm run dev
   ```

## Firebase Setup

1. Create a Firebase project at [firebase.google.com](https://firebase.google.com)
2. Navigate to the Console and click "Add project"
3. Follow the setup wizard to configure your project
4. Once created, click on "Web" (</>) to add a web app to your project
5. Register your app with a nickname (e.g., "vite-template")
6. Copy the Firebase configuration object provided

### Setting up Authentication:

1. In the Firebase Console, navigate to "Authentication" > "Sign-in method"
2. Enable Email/Password and Google authentication providers
3. For Google, configure the OAuth consent screen if required

### Setting up Firestore (Optional):

1. Go to "Firestore Database" in the Firebase Console
2. Click "Create database"
3. Choose between production or test mode (test mode for development)
4. Select a location for your database

### Setting up Storage:

1. Go to "Storage" in the Firebase Console
2. Click "Get started"
3. Configure storage rules for your application

### Update Configuration

Replace the placeholder configuration in `src/firebase.js` with your actual Firebase config:

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

## Theme Usage

This template comes with a pre-configured Material UI theme based on the Outstaffer design system. The theme includes:

- **Color System**: A comprehensive color palette with primary, secondary, and UI colors
- **Typography**: Font families, sizes, weights, and line heights
- **Spacing**: Consistent spacing scale
- **Component Styling**: Pre-styled MUI components
- **Responsive Design**: Mobile-first approach

### Using the Theme

The theme is automatically applied to all Material UI components. To use theme values in your components:

```jsx
import { useTheme } from '@mui/material/styles';
import { CustomColors } from '../theme';

function MyComponent() {
  const theme = useTheme();
  
  return (
    <div style={{ 
      backgroundColor: theme.palette.background.default,
      color: CustomColors.MidnightBlue,
      padding: theme.spacing(2)
    }}>
      Themed content
    </div>
  );
}
```

### Theme Constants

The theme exports several constants that can be imported and used:

```jsx
import { 
  CustomColors,
  FontSize, 
  Spacing, 
  BorderRadius 
} from '../theme';

// Usage example
<div style={{ 
  fontSize: FontSize.Large,
  padding: Spacing.Medium,
  borderRadius: BorderRadius.Rounded
}}>
  Content with theme constants
</div>
```