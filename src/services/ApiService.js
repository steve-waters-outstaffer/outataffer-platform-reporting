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

// Customer metrics endpoints
export const fetchLatestCustomerMetrics = async () => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/customers/latest?_=${timestamp}`);
    } catch (error) {
        console.warn("Customer API error, using fallback data:", error);
        // Return hardcoded fallback data for development
        return [
            {"snapshot_date":"2025-04-02","metric_type":"total_customers","id":"total_customers","label":"Total Customers","count":42,"value_aud":null,"percentage":null,"rank":null},
            {"snapshot_date":"2025-04-02","metric_type":"active_customers","id":"active_customers","label":"Active Customers","count":38,"value_aud":null,"percentage":90.5,"rank":null},
            {"snapshot_date":"2025-04-02","metric_type":"new_customers","id":"new_customers","label":"New Customers This Month","count":2,"value_aud":null,"percentage":4.8,"rank":null},
            {"snapshot_date":"2025-04-02","metric_type":"churned_customers","id":"churned_customers","label":"Churned Customers","count":1,"value_aud":null,"percentage":2.4,"rank":null},
            {"snapshot_date":"2025-04-02","metric_type":"active_contracts","id":"active_contracts","label":"Active Contracts","count":126,"value_aud":null,"percentage":null,"rank":null},
            {"snapshot_date":"2025-04-02","metric_type":"avg_contracts_per_customer","id":"avg_contracts_per_customer","label":"Average Contracts per Customer","count":3,"value_aud":null,"percentage":null,"rank":null},
            {"snapshot_date":"2025-04-02","metric_type":"avg_arr_per_customer","id":"avg_arr_per_customer","label":"Average ARR per Customer","count":null,"value_aud":25711.56,"percentage":null,"rank":null},
            {"snapshot_date":"2025-04-02","metric_type":"revenue_concentration","id":"revenue_concentration","label":"Top 10 Customer Revenue %","count":null,"value_aud":null,"percentage":72.4,"rank":null}
        ];
    }
};

export const fetchTopCustomers = async (limit = 10) => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/customers/top-customers?limit=${limit}&_=${timestamp}`);
    } catch (error) {
        console.warn("Top customers API error, using fallback data:", error);
        // Return hardcoded fallback data for development
        return [
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company123","label":"Global Tech Solutions","count":15,"value_aud":124500.0,"percentage":12.75,"rank":1},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company456","label":"Pacific Digital Services","count":12,"value_aud":98750.0,"percentage":10.12,"rank":2},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company789","label":"Asia Connect Partners","count":10,"value_aud":87300.0,"percentage":8.94,"rank":3},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company012","label":"Oceanic Business Systems","count":9,"value_aud":76200.0,"percentage":7.81,"rank":4},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company345","label":"Eastern Digital Solutions","count":8,"value_aud":68500.0,"percentage":7.02,"rank":5},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company678","label":"Manila Tech Hub","count":7,"value_aud":62400.0,"percentage":6.39,"rank":6},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company901","label":"Bangkok Data Services","count":6,"value_aud":54800.0,"percentage":5.62,"rank":7},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company234","label":"Singapore Solutions Group","count":5,"value_aud":48700.0,"percentage":4.99,"rank":8},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company567","label":"Vietnam IT Services","count":4,"value_aud":43200.0,"percentage":4.43,"rank":9},
            {"snapshot_date":"2025-04-02","metric_type":"top_customer","id":"company890","label":"Australian Digital Agency","count":3,"value_aud":38900.0,"percentage":3.99,"rank":10}
        ];
    }
};

export const fetchCustomerTrend = async (months = 6) => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/customers/trend?months=${months}&_=${timestamp}`);
    } catch (error) {
        console.warn("Customer trend API error, using fallback data:", error);
        // Return mock trend data for development
        return [
            { month: "Nov 2024", value: 28, date: "2024-11-30" },
            { month: "Dec 2024", value: 31, date: "2024-12-31" },
            { month: "Jan 2025", value: 34, date: "2025-01-31" },
            { month: "Feb 2025", value: 36, date: "2025-02-28" },
            { month: "Mar 2025", value: 38, date: "2025-03-31" },
            { month: "Apr 2025", value: null, date: "2025-04-30" }
        ];
    }
};

// Add these to your src/services/ApiService.js file

// Get company size distribution
export const fetchCompanySizeMetrics = async () => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/customers/company-sizes?_=${timestamp}`);
    } catch (error) {
        console.warn("Company size metrics API error, using fallback data:", error);
        // Return hardcoded fallback data for development
        return [
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_distribution", "id":"SIZE_0", "label":"Small Medium Business", "count":26, "value_aud":420122.57, "percentage":61.9, "rank":1},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_arr", "id":"SIZE_ARR_0", "label":"ARR: Small Medium Business", "count":0, "value_aud":420122.57, "percentage":43.0, "rank":1},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_avg_arr", "id":"SIZE_AVG_0", "label":"Avg ARR: Small Medium Business", "count":0, "value_aud":16158.56, "percentage":null, "rank":1},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_distribution", "id":"SIZE_1", "label":"Small Business", "count":9, "value_aud":82564.91, "percentage":21.43, "rank":2},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_arr", "id":"SIZE_ARR_1", "label":"ARR: Small Business", "count":0, "value_aud":82564.91, "percentage":8.45, "rank":2},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_avg_arr", "id":"SIZE_AVG_1", "label":"Avg ARR: Small Business", "count":0, "value_aud":9173.88, "percentage":null, "rank":2},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_distribution", "id":"SIZE_2", "label":"Medium Business", "count":6, "value_aud":290697.49, "percentage":14.29, "rank":3},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_arr", "id":"SIZE_ARR_2", "label":"ARR: Medium Business", "count":0, "value_aud":290697.49, "percentage":29.75, "rank":3},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_avg_arr", "id":"SIZE_AVG_2", "label":"Avg ARR: Medium Business", "count":0, "value_aud":48449.58, "percentage":null, "rank":3},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_distribution", "id":"SIZE_3", "label":"Corporate", "count":1, "value_aud":183654.24, "percentage":2.38, "rank":4},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_arr", "id":"SIZE_ARR_3", "label":"ARR: Corporate", "count":0, "value_aud":183654.24, "percentage":18.8, "rank":4},
            {"snapshot_date":"2025-04-05", "metric_type":"company_size_avg_arr", "id":"SIZE_AVG_3", "label":"Avg ARR: Corporate", "count":0, "value_aud":183654.24, "percentage":null, "rank":4}
        ];
    }
};

// Get top industries by count
export const fetchIndustriesByCount = async (limit = 10) => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/customers/industries-by-count?limit=${limit}&_=${timestamp}`);
    } catch (error) {
        console.warn("Industries by count API error, using fallback data:", error);
        // Return hardcoded fallback data for development
        return [
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_count", "id":"IND_COUNT_0", "label":"Construction", "count":22, "value_aud":300659.28, "percentage":52.38, "rank":1},
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_count", "id":"IND_COUNT_1", "label":"EdTech (Educational Technology)", "count":3, "value_aud":49200.0, "percentage":7.14, "rank":2},
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_count", "id":"IND_COUNT_2", "label":"Software as a Service (SaaS)", "count":3, "value_aud":222032.05, "percentage":7.14, "rank":3},
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_count", "id":"IND_COUNT_3", "label":"IT Consulting", "count":3, "value_aud":22950.11, "percentage":7.14, "rank":4}
        ];
    }
};

// Get top industries by ARR
export const fetchIndustriesByArr = async (limit = 10) => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/customers/industries-by-arr?limit=${limit}&_=${timestamp}`);
    } catch (error) {
        console.warn("Industries by ARR API error, using fallback data:", error);
        // Return hardcoded fallback data for development
        return [
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_arr", "id":"IND_ARR_0", "label":"Construction", "count":22, "value_aud":300659.28, "percentage":30.77, "rank":1},
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_arr", "id":"IND_ARR_1", "label":"Software as a Service (SaaS)", "count":3, "value_aud":222032.05, "percentage":22.72, "rank":2},
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_arr", "id":"IND_ARR_2", "label":"Staffing & Recruiting", "count":1, "value_aud":183654.24, "percentage":18.8, "rank":3},
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_arr", "id":"IND_ARR_3", "label":"E-commerce", "count":1, "value_aud":50100.0, "percentage":5.13, "rank":4},
            {"snapshot_date":"2025-04-05", "metric_type":"top_industry_by_arr", "id":"IND_ARR_4", "label":"EdTech (Educational Technology)", "count":3, "value_aud":49200.0, "percentage":5.04, "rank":5}
        ];
    }
};

// Add to ApiService.js

export const fetchRevenueByCountry = async () => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/revenue/countries?_=${timestamp}`);
    } catch (error) {
        console.warn("Revenue by country API error, using fallback data:", error);
        // Fallback data if the API fails
        return [
            {
                "name": "Philippines",
                "trend": [
                    {
                        "month": "Apr 2025",
                        "active_subscriptions": 96,
                        "total_mrr": 58904.60,
                        "date": "2025-04-08"
                    }
                ]
            },
            {
                "name": "Thailand",
                "trend": [
                    {
                        "month": "Apr 2025",
                        "active_subscriptions": 8,
                        "total_mrr": 4398.0,
                        "date": "2025-04-08"
                    }
                ]
            },
            {
                "name": "Vietnam",
                "trend": [
                    {
                        "month": "Apr 2025",
                        "active_subscriptions": 5,
                        "total_mrr": 3235.5,
                        "date": "2025-04-08"
                    }
                ]
            },
            {
                "name": "Australia",
                "trend": [
                    {
                        "month": "Apr 2025",
                        "active_subscriptions": 1,
                        "total_mrr": 825.7,
                        "date": "2025-04-08"
                    }
                ]
            }
        ];
    }
};

export const fetchGeographicMetrics = async () => {
    try {
        const timestamp = new Date().getTime();
        return apiRequest(`/geography/countries?_=${timestamp}`);
    } catch (error) {
        console.warn("Geographic metrics API error, using fallback data:", error);
        // Return a minimal structure for development/fallback
        return {
            snapshot_date: "2025-04-09",
            countries: [],
            totals: {
                active_contracts: 0,
                offboarding_contracts: 0,
                approved_not_started: 0,
                mrr: 0,
                arr: 0
            }
        };
    }
};