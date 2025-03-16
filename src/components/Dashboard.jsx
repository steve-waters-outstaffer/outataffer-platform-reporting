// src/components/Dashboard.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { logoutUser } from '../services/AuthService.js';
import Chart from './Chart';

const Dashboard = () => {
    const { currentUser } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        try {
            await logoutUser();
            navigate('/login');
        } catch (error) {
            console.error("Logout error:", error);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <nav className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex items-center">
                            <h1 className="text-xl font-semibold">Firebase + Vite Template</h1>
                        </div>
                        <div className="flex items-center">
                            <span className="mr-4 text-sm text-gray-600">
                                {currentUser?.email}
                            </span>
                            <button
                                onClick={handleLogout}
                                className="bg-white hover:bg-gray-100 text-gray-800 font-semibold py-2 px-4 border border-gray-300 rounded shadow text-sm"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <h2 className="text-2xl font-semibold mb-4">Dashboard</h2>
                    <p className="text-gray-600 mb-4">
                        Welcome to your dashboard! Below is an example chart created with ECharts.
                    </p>
                </div>

                <div className="bg-white shadow rounded-lg p-6">
                    <h3 className="text-xl font-semibold mb-4">Sample Chart</h3>
                    <div className="h-96">
                        <Chart />
                    </div>
                </div>
            </main>
        </div>
    );
};

export default Dashboard;