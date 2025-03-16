# Firebase Vite Template

A modern, production-ready template for quickly building Firebase applications with React, Vite, Tailwind CSS v4, and ECharts.

## Features

- 🔥 **Firebase Integration** - Authentication, Storage, and optional Firestore
- 🚀 **Vite** - Lightning fast builds and HMR
- 🎨 **Tailwind CSS v4** - The latest version of Tailwind for styling
- 📊 **ECharts** - Powerful charting library with geographic map support
- 🔒 **Authentication** - Email/password and Google sign-in with protected routes
- 📱 **Responsive Design** - Mobile-friendly interface
- 🧩 **Component Structure** - Organized component architecture

## Technologies

| Category           | Technology                                  |
|--------------------|---------------------------------------------|
| Framework          | React 19                                    |
| Build Tool         | Vite 6.2+                                   |
| CSS Framework      | Tailwind CSS v4                             |
| Authentication     | Firebase Authentication                      |
| Database (Optional)| Firestore                                   |
| File Storage       | Firebase Storage                            |
| Routing            | React Router v6                             |
| Charts             | ECharts                                     |

## Getting Started

1. Clone this repository
2. Install dependencies:
   ```bash
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

## Project Structure

```
project-root/
├── src/
│   ├── components/
│   │   ├── auth/
│   │   │   ├── AuthContainer.jsx   # Auth wrapper component
│   │   │   ├── Login.jsx           # Login form
│   │   │   ├── Register.jsx        # Registration form
│   │   │   └── ProtectedRoute.jsx  # Route protection component
│   │   ├── Chart.jsx               # ECharts component
│   │   └── Dashboard.jsx           # Main app dashboard
│   ├── contexts/
│   │   └── AuthContext.jsx         # Authentication context
│   ├── services/
│   │   └── authService.js          # Auth helper functions
│   ├── App.jsx                     # Main application component
│   ├── main.jsx                    # Application entry point
│   ├── firebase.js                 # Firebase configuration
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

### Styling

This template uses Tailwind CSS v4 for styling. You can customize the design by editing:
- `tailwind.config.js` for theme customization
- `src/index.css` for global styles

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

This template is MIT licensed.