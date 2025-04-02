// src/services/ApiService.js
const API_KEY = 'dJ8fK2sP9qR5xV7zT3mA6cE1bN';
const BASE_URL = 'https://dashboards-ccc88.ts.r.appspot.com';

// Helper function for API requests
const apiRequest = async (endpoint, options = {}) => {
    const defaultHeaders = {
        'X-API-KEY': API_KEY,
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
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

// Revenue metrics endpoints
export const fetchLatestRevenueMetrics = async () => {
    try {
        // Add timestamp to prevent caching
        const timestamp = new Date().getTime();
        return apiRequest(`/revenue/latest?_=${timestamp}`);
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
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/revenue/trend?months=${months}&_=${timestamp}`);
    } catch (error) {
        console.warn("Revenue trend API error, using fallback data:", error);
        // Return mock trend data for development
        return [
            { month: "Jan 2025", value: 62000, date: "2025-01-31" },
            { month: "Feb 2025", value: 66000, date: "2025-02-28" },
            { month: "Mar 2025", value: 81420, date: "2025-03-31" },
            { month: "Apr 2025", value: null, date: "2025-04-30" }
        ];
    }
};

export const fetchSubscriptionTrend = async (months = 6) => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/revenue/subscription-trend?months=${months}&_=${timestamp}`);
    } catch (error) {
        console.warn("Subscription trend API error, using fallback data:", error);
        // Return mock trend data for development
        return [
            { month: "Jan 2025", value: 105, date: "2025-01-31" },
            { month: "Feb 2025", value: 118, date: "2025-02-28" },
            { month: "Mar 2025", value: 124, date: "2025-03-31" },
            { month: "Apr 2025", value: null, date: "2025-04-30" }
        ];
    }
};

// Add-on metrics endpoints
export const fetchLatestAddonMetrics = async () => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/addons/latest?_=${timestamp}`);
    } catch (error) {
        console.warn("Add-on metrics API error, using fallback data:", error);
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
export const fetchLatestHealthInsuranceMetrics = async (cacheBustQuery = '') => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/health-insurance/latest?_=${timestamp}${cacheBustQuery || ''}`);
    } catch (error) {
        console.warn("Health insurance API error, falling back to manual JSON data:", error);
        // Return the exact JSON from Postman as a fallback
        return [
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_plan_by_country","id":"SAFETY_WING_PREMIUM","label":"Safety Wing Premium (PH)","count":1,"overall_percentage":0.9259259259259258,"category_percentage":100.0,"contract_count":1},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_plan_by_country","id":"SAFETY_WING_PREMIUM","label":"Safety Wing Premium (AU)","count":2,"overall_percentage":66.66666666666666,"category_percentage":100.0,"contract_count":2},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_total_by_country","id":"AU","label":"AU","count":2,"overall_percentage":66.66666666666666,"category_percentage":100.0,"contract_count":2},
            {"snapshot_date":"2025-04-02","metric_type":"eligible_contracts_by_country","id":"AU","label":"AU","count":3,"overall_percentage":0.0,"category_percentage":0.0,"contract_count":3},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_plan_by_country","id":"SAFETY_WING_STANDARD","label":"Safety Wing Standard (VN)","count":7,"overall_percentage":100.0,"category_percentage":100.0,"contract_count":7},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_total_by_country","id":"VN","label":"VN","count":7,"overall_percentage":100.0,"category_percentage":100.0,"contract_count":7},
            {"snapshot_date":"2025-04-02","metric_type":"eligible_contracts_by_country","id":"VN","label":"VN","count":7,"overall_percentage":0.0,"category_percentage":0.0,"contract_count":7},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_plan_by_country","id":"AIA_PLAN_3","label":"Core Plus Plan (TH)","count":8,"overall_percentage":100.0,"category_percentage":100.0,"contract_count":8},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_total_by_country","id":"TH","label":"TH","count":8,"overall_percentage":100.0,"category_percentage":100.0,"contract_count":8},
            {"snapshot_date":"2025-04-02","metric_type":"eligible_contracts_by_country","id":"TH","label":"TH","count":8,"overall_percentage":0.0,"category_percentage":0.0,"contract_count":8},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_plan_by_country","id":"LOCAL","label":"Health Insurance  (PH)","count":107,"overall_percentage":99.07407407407408,"category_percentage":100.0,"contract_count":107},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_total_by_country","id":"PH","label":"PH","count":108,"overall_percentage":100.0,"category_percentage":100.0,"contract_count":108},
            {"snapshot_date":"2025-04-02","metric_type":"eligible_contracts_by_country","id":"PH","label":"PH","count":108,"overall_percentage":0.0,"category_percentage":0.0,"contract_count":108},
            {"snapshot_date":"2025-04-02","metric_type":"health_insurance_dependents_by_country","id":"PH","label":"PH","count":40,"overall_percentage":37.03703703703704,"category_percentage":100.0,"contract_count":108}
        ];
    }
};

// General health check
export const checkApiHealth = async () => {
    try {
        const timestamp = new Date().getTime();
        const response = await apiRequest(`/health?_=${timestamp}`);
        return { status: 'ok', isLive: true, ...response };
    } catch (error) {
        console.warn("API health check failed:", error);
        return { status: 'offline', isLive: false };
    }
};