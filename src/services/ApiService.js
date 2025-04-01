// src/services/ApiService.js
const API_KEY = 'your-simple-internal-api-key';
const BASE_URL = 'https://your-project-id.appspot.com';

export const fetchSubscriptionMetrics = async () => {
    const res = await fetch(`${BASE_URL}/subscription_metrics`, {
        headers: { 'X-API-KEY': API_KEY }
    });

    if (!res.ok) throw new Error('API fetch error');
    return res.json();
};
