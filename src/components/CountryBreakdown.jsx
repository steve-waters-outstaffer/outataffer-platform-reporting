// New component to add to your RevenueDashboard.jsx
import React, { useState, useEffect } from 'react';
import { Box, Grid, Paper, Typography, Divider, Card, CardContent } from '@mui/material';
import EChartsComponent from './Chart';
import { CustomColors } from '../theme';
import { fetchRevenueByCountry } from '../services/ApiService';

const CountryBreakdown = () => {
    const [countryData, setCountryData] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
    const fetchData = async () => {
try {
setLoading(true);
setError(null);
const data = await fetchRevenueByCountry();
setCountryData(data);
setLoading(false);
} catch (err) {
console.error("Error fetching country revenue data:", err);
setError("Failed to load country revenue data");
setLoading(false);
}
};

fetchData();
}, []);

// Format currency values
const formatCurrency = (value) => {
return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 0
}).format(value);
};

// Format percentage values
const formatPercentage = (value) => {
return `${value.toFixed(1)}%`;
};

// Get country flag emoji
const getCountryFlag = (countryCode) => {
const codePoints = countryCode
.toUpperCase()
.split('')
.map(char => 127397 + char.charCodeAt());
return String.fromCodePoint(...codePoints);
};

// Chart options for country breakdown
const getCountryChartOptions = () => {
if (!countryData.length) return {};

// Limit to top 8 countries for the chart
    const chartData = [...countryData]
.sort((a, b) => b.value_aud - a.value_aud)
.slice(0, 8);

return {
    title: {
        text: 'Annual Recurring Revenue by Country',
        left: 'center',
        textStyle: {
            color: CustomColors.UIGrey800
        }
    },
    tooltip: {
        trigger: 'axis',
        axisPointer: {
            type: 'shadow'
        },
        formatter: (params) => {
    const data = params[0];
return `${data.name}: ${formatCurrency(data.value)} (${formatPercentage(data.percentage)})`;
}
},
grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
},
xAxis: {
    type: 'value',
    axisLabel: {
formatter: (value) => formatCurrency(value)
}
},
yAxis: {
    type: 'category',
    data: chartData.map(item => item.label),
axisLabel: {
color: CustomColors.UIGrey700
}
},
series: [
    {
name: 'ARR',
type: 'bar',
data: chartData.map(item => ({
    value: item.value_aud,
    percentage: item.percentage
})),
itemStyle: {
    color: CustomColors.DeepSkyBlue
},
label: {
    show: true,
    position: 'right',
    formatter: (params) => formatCurrency(params.value)
}
}
]
};
};

if (loading) {
return <Box sx={{ p: 3, textAlign: 'center' }}>Loading country data...</Box>;
}

if (error) {
return <Box sx={{ p: 3, color: 'error.main' }}>{error}</Box>;
}

return (
    <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
    <Typography variant="h5" gutterBottom>Revenue by Country</Typography>
    <Divider sx={{ mb: 2 }} />

    {/* Country bar chart */}
    <Box sx={{ height: 400, mb: 4 }}>
    <EChartsComponent option={getCountryChartOptions()} />
</Box>

  {/* Country cards */}
<Grid container spacing={2}>
                        {countryData.map((country) => (
    <Grid item xs={12} sm={6} md={4} lg={3} key={country.id}>
    <Card sx={{
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    borderLeft: `4px solid ${country.value_aud > 0 ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300}`
    }}>
    <CardContent>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
    <Typography variant="h6" component="div" gutterBottom>
    {country.label}
    </Typography>
    <Typography variant="h3" sx={{ fontSize: '2rem' }}>
    {getCountryFlag(country.id)}
</Typography>
  </Box>
    <Typography variant="body" color="text.secondary" gutterBottom>
                                                      Subscriptions: <strong>{country.count}</strong>
                                                                                              </Typography>
                                                                                                <Typography variant="h5" component="div" sx={{
    color: country.value_aud > 0 ? CustomColors.MidnightBlue : CustomColors.UIGrey500
}}>
{formatCurrency(country.value_aud)}
</Typography>
  <Typography variant="bodySmall" color="text.secondary">
                                        {formatPercentage(country.percentage)} of total ARR
                                                                                        </Typography>
                                                                                          </CardContent>
                                                                                            </Card>
                                                                                              </Grid>
))}
</Grid>
  </Paper>
);
};

export default CountryBreakdown;