// CountryBreakdown.jsx - updated to include countries with zero revenue/subscriptions
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

                // Transform API data into the required format
                // Include ALL countries, even those with 0 subscriptions/revenue
                const transformedData = data.map(country => {
                    // Get the latest trend data (should be current month)
                    const latestTrend = country.trend[0] || {};

                    return {
                        id: country.name, // Use name as ID
                        label: country.name,
                        count: latestTrend.active_subscriptions || 0,
                        value_aud: latestTrend.total_mrr || 0,
                        percentage: 0 // Will calculate this later
                    };
                });

                // Calculate percentage of total
                const totalValue = transformedData.reduce((sum, item) => sum + item.value_aud, 0);
                const dataWithPercentage = transformedData.map(item => ({
                    ...item,
                    percentage: totalValue > 0 ? (item.value_aud / totalValue) * 100 : 0
                }));

                setCountryData(dataWithPercentage);
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

    // Get country flag emoji - ensure countryCode is defined before using it
    const getCountryFlag = (countryCode) => {
        if (!countryCode) return '🌎'; // Default globe emoji if no country code

        // Handle some manual mappings for clearer flags
        const countryMap = {
            'Australia': 'AU',
            'Philippines': 'PH',
            'Vietnam': 'VN',
            'Thailand': 'TH',
            'Singapore': 'SG',
            'Malaysia': 'MY',
            'India': 'IN'
        };

        // Get 2-letter code, either directly or from our map
        const code = countryMap[countryCode] || countryCode;

        try {
            const codePoints = code
                .toUpperCase()
                .split('')
                .map(char => 127397 + char.charCodeAt());
            return String.fromCodePoint(...codePoints);
        } catch (err) {
            console.error(`Error creating flag for country: ${countryCode}`, err);
            return '🌎';
        }
    };

    // Chart options for country breakdown
    const getCountryChartOptions = () => {
        if (!countryData.length) return {};

        // Get all countries for the chart, sorted by value
        const chartData = [...countryData]
            .sort((a, b) => b.value_aud - a.value_aud);

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
                inverse: true,
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
                        color: (params) => {
                            // Use a lighter color for zero values
                            return params.value > 0 ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300;
                        }
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

    // Sort countries for display - active ones first, then alphabetically
    const sortedCountryData = [...countryData].sort((a, b) => {
        // First by revenue (descending)
        if (b.value_aud !== a.value_aud) {
            return b.value_aud - a.value_aud;
        }
        // Then by subscription count (descending)
        if (b.count !== a.count) {
            return b.count - a.count;
        }
        // Finally alphabetically
        return a.label.localeCompare(b.label);
    });

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
                {sortedCountryData.map((country) => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={country.id}>
                        <Card sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            borderLeft: `4px solid ${country.value_aud > 0 ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300}`,
                            opacity: country.value_aud > 0 ? 1 : 0.8 // Slightly fade zero-value countries
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
                                    {country.value_aud > 0 ? formatPercentage(country.percentage) : '0.0%'} of total ARR
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