// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '/src/contexts/AuthContext';
import Dashboard from './components/Dashboard';
import AuthContainer from './components/auth/AuthContainer';
import ProtectedRoute from './components/auth/ProtectedRoute';

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <Routes>
                    <Route path="/login" element={<AuthContainer />} />
                    <Route path="/dashboard" element={
                        <ProtectedRoute>
                            <Dashboard />
                        </ProtectedRoute>
                    } />
                    <Route path="/" element={<Navigate replace to="/dashboard" />} />
                </Routes>
            </AuthProvider>
        </BrowserRouter>
    );
}

export default App;