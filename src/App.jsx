// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, StyledEngineProvider, CssBaseline } from '@mui/material';
import { AuthProvider } from '/src/contexts/AuthContext';
import Dashboard from './components/Dashboard';
import RevenueDashboard from './components/RevenueDashboard';
import AddonsDashboard from './components/AddonsDashboard';
import RequisitionDashboard from './components/RequisitionDashboard';
import HealthInsuranceDashboard from './components/HealthInsuranceDashboard';
import AuthContainer from './components/auth/AuthContainer';
import CustomerDashboard from './components/CustomerDashboard';
import GeographicDashboard from './components/GeographicDashboard';
import ProtectedRoute from './components/auth/ProtectedRoute';
import { theme } from './theme';

function App() {
    return (
        <StyledEngineProvider injectFirst>
            <ThemeProvider theme={theme}>
                <CssBaseline />
                <BrowserRouter>
                    <AuthProvider>
                        <Routes>
                            <Route path="/login" element={<AuthContainer />} />
                            <Route path="/dashboard" element={
                                <ProtectedRoute>
                                    <Dashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/revenue-dashboard" element={
                                <ProtectedRoute>
                                    <RevenueDashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/addons-dashboard" element={
                                <ProtectedRoute>
                                    <AddonsDashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/requisitions-dashboard" element={
                                <ProtectedRoute>
                                    <RequisitionDashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/health-dashboard" element={
                                <ProtectedRoute>
                                    <HealthInsuranceDashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/customer-dashboard" element={
                                <ProtectedRoute>
                                    <CustomerDashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/geographic-dashboard" element={
                                <ProtectedRoute>
                                    <GeographicDashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/" element={<Navigate replace to="/dashboard" />} />
                        </Routes>
                    </AuthProvider>
                </BrowserRouter>
            </ThemeProvider>
        </StyledEngineProvider>
    );
}

export default App;