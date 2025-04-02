// src/services/ApiService.js
const API_KEY = 'dJ8fK2sP9qR5xV7zT3mA6cE1bN';
const BASE_URL = 'https://dashboards-ccc88.ts.r.appspot.com';

// Helper function for API requests
const apiRequest = async (endpoint, options = {}) => {
    const defaultHeaders = {
        'X-API-KEY': API_KEY,
        'Content-Type': 'application/json'
    };

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...(options.headers || {})
        }
    };

    try {
        const response = await fetch(`${BASE_URL}${endpoint}`, config);

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'API request failed');
        }

        return response.json();
    } catch (error) {
        console.error(`API error for ${endpoint}:`, error);
        throw error;
    }
};

// Revenue metrics endpoints - match the actual endpoints from main.py
export const fetchLatestRevenueMetrics = async () => {
    try {
        // Call the actual endpoint now that it's working
        return apiRequest('/revenue/latest');
    } catch (error) {
        console.warn("Revenue API error, using fallback data:", error);
        // Return hardcoded data as a fallback during development
        return {
            "snapshot_date": "2025-03-31",
            "total_active_subscriptions": 99,
            "approved_not_started": 1,
            "offboarding_contracts": 2,
            "total_contracts": 127,
            "revenue_generating_contracts": 126,
            "new_subscriptions": 3,
            "churned_subscriptions": 3,
            "retention_rate": 97.62,
            "churn_rate": 2.38,
            "eor_fees_mrr": 56997.13,
            "device_fees_mrr": 13538.38,
            "hardware_fees_mrr": 613.37,
            "software_fees_mrr": 79.14,
            "health_insurance_mrr": 10191.92,
            "placement_fees_monthly": 6077.88,
            "total_mrr": 81419.93,
            "total_monthly_revenue": 87497.81,
            "total_arr": 977039.21,
            "avg_subscription_value": 646.19,
            "recurring_revenue_percentage": 93.05,
            "one_time_revenue_percentage": 6.95,
            "total_customers": 42,
            "new_customers_this_month": 0,
            "addon_revenue_percentage": 29.99,
            "avg_days_from_approval_to_start": -224.74,
            "avg_days_until_start": 7.0,
            "plan_change_rate": 0.0,
            "laptops_count": 58,
            "contracts_with_dependents": 34,
            "avg_dependents_per_contract": 1.18
        };
    }
};

export const fetchRevenueTrend = async (months = 6) => {
    // Return mock trend data for development
    return [
        { month: "Jan 2025", value: 62000, date: "2025-01-31" },
        { month: "Feb 2025", value: 66000, date: "2025-02-28" },
        { month: "Mar 2025", value: 81420, date: "2025-03-31" },
        { month: "Apr 2025", value: null, date: "2025-04-30" }
    ];
    // In production:
    // return apiRequest(`/revenue/trend?months=${months}`);
};

export const fetchSubscriptionTrend = async (months = 6) => {
    // Return mock trend data for development
    return [
        { month: "Jan 2025", value: 105, date: "2025-01-31" },
        { month: "Feb 2025", value: 118, date: "2025-02-28" },
        { month: "Mar 2025", value: 124, date: "2025-03-31" },
        { month: "Apr 2025", value: null, date: "2025-04-30" }
    ];
    // In production:
    // return apiRequest(`/revenue/subscription-trend?months=${months}`);
};

// Add-on metrics endpoints
export const fetchLatestAddonMetrics = async () => {
    try {
        // Check if API is up
        await apiRequest('/health');
        // For production:
        // return apiRequest('/addons/latest');
        throw new Error("Using development fallback data");
    } catch (error) {
        // Import local data during development
        return import('../components/addons_data.json')
            .then(module => module.default)
            .catch(err => {
                console.error("Error loading local data:", err);
                return []; // Return empty array if local data fails
            });
    }
};

// Health insurance metrics endpoints
export const fetchLatestHealthInsuranceMetrics = async () => {
    // In production:
    // return apiRequest('/health_insurance/latest');

    // For development, return mock data
    return [
        {
            "snapshot_date": "2025-03-31",
            "metric_type": "health_insurance_plan",
            "id": "STANDARD",
            "label": "Standard Health Plan",
            "count": 67,
            "overall_percentage": 53.2,
            "category_percentage": 100.0,
            "contract_count": 67
        },
        {
            "snapshot_date": "2025-03-31",
            "metric_type": "health_insurance_plan",
            "id": "PREMIUM",
            "label": "Premium Health Plan",
            "count": 34,
            "overall_percentage": 27.0,
            "category_percentage": 100.0,
            "contract_count": 34
        }
    ];
};

// General health check
export const checkApiHealth = async () => {
    try {
        const response = await apiRequest('/health');
        return { status: 'ok', isLive: true, ...response };
    } catch (error) {
        console.warn("API health check failed:", error);
        return { status: 'offline', isLive: false };
    }
};