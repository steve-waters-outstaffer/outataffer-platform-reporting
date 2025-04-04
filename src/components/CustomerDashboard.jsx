// src/components/CustomerDashboard.jsx
import React, { useState, useEffect } from 'react';
import {
    Box,
    Grid,
    Paper,
    Typography,
    Card,
    CardContent,
    Divider,
    CircularProgress,
    Container,
    Table,
    TableHead,
    TableBody,
    TableRow,
    TableCell,
    Button,
    Alert
} from '@mui/material';
import * as echarts from 'echarts';
import EChartsComponent from './Chart';
import { CustomColors } from '../theme';
import { fetchLatestCustomerMetrics, fetchTopCustomers, fetchCustomerTrend } from '../services/ApiService';
import { useNavigate } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

const CustomerDashboard = () => {
    const navigate = useNavigate();
    const [customerData, setCustomerData] = useState([]);
    const [topCustomers, setTopCustomers] = useState([]);
    const [customerTrend, setCustomerTrend] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                // Fetch all data in parallel
                const [metricsData, topCustomersData, trendData] = await Promise.all([
                    fetchLatestCustomerMetrics(),
                    fetchTopCustomers(10), // Top 10 customers
                    fetchCustomerTrend(6) // Last 6 months
                ]);

                setCustomerData(metricsData);
                setTopCustomers(topCustomersData);
                setCustomerTrend(trendData);
                setLoading(false);
            } catch (err) {
                console.error("Error fetching customer dashboard data:", err);
                setError("Failed to load customer dashboard data. Please try again later.");
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    // Helper functions to find metric values
    const findMetric = (metricType) => {
        return customerData.find(item => item.metric_type === metricType) || {};
    };

    // Format currency values
    const formatCurrency = (value) => {
        if (value === null || value === undefined) return '-';
        return new Intl.NumberFormat('en-AU', {
            style: 'currency',
            currency: 'AUD',
            maximumFractionDigits: 0
        }).format(value);
    };

    // Format percentage values
    const formatPercentage = (value) => {
        if (value === null || value === undefined) return '-';
        return `${value.toFixed(1)}%`;
    };

    // Customer trend chart options
    const getCustomerTrendOptions = () => {
        // Use the actual API data if available, otherwise use placeholder
        const months = customerTrend.map(item => item.month);
        const values = customerTrend.map(item => item.value);

        // Find the latest month index
        const currentMonthIndex = customerTrend.length - 1;

        return {
            title: {
                text: 'Active Customers Trend',
                left: 'center',
                textStyle: {
                    color: CustomColors.UIGrey800
                }
            },
            tooltip: {
                trigger: 'axis',
                formatter: params => `${params[0].name}: ${params[0].value} customers`
            },
            grid: {
                left: '10%',
                right: '4%',
                bottom: '15%',
                top: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: months,
                axisLabel: {
                    color: CustomColors.UIGrey700,
                    margin: 14
                }
            },
            yAxis: {
                type: 'value',
                min: function(value) {
                    return Math.max(0, value.min - 5); // Ensure no negative values & some padding
                },
                axisLabel: {
                    formatter: value => value
                }
            },
            series: [
                {
                    name: 'Active Customers',
                    type: 'line',
                    data: values,
                    symbol: 'circle',
                    symbolSize: (value, params) => (params.dataIndex === currentMonthIndex ? 10 : 6),
                    lineStyle: {
                        color: CustomColors.MidnightBlue,
                        width: 3
                    },
                    itemStyle: {
                        color: (params) => {
                            return params.dataIndex === currentMonthIndex
                                ? CustomColors.DeepSkyBlue
                                : CustomColors.MidnightBlue;
                        },
                        borderColor: CustomColors.UIGrey600,
                        borderWidth: 1
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(0, 174, 216, 0.5)' },
                            { offset: 1, color: 'rgba(0, 174, 216, 0.1)' }
                        ])
                    }
                }
            ]
        };
    };

    const getCustomerConcentrationOptions = () => {
        if (!topCustomers || topCustomers.length === 0) return {};

        const data = topCustomers
            .map(c => ({
                name: c.label,
                value: c.value_aud,
                percentage: c.percentage
            }))
            .sort((a, b) => b.value - a.value);

        return {
            title: {
                text: 'Top 10 ARR',
                left: 'center',
                textStyle: {
                    color: CustomColors.UIGrey800
                }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: (params) => {
                    const { name, value, data } = params[0];
                    return `${name}<br/>ARR: ${formatCurrency(value)}<br/>Share: ${formatPercentage(data.percentage)}`;
                }
            },
            grid: {
                left: '25%',
                right: '5%',
                bottom: '5%',
                top: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'value',
                axisLabel: {
                    formatter: value => `$${(value / 1000).toFixed(0)}k`,
                    color: CustomColors.UIGrey700
                }
            },
            yAxis: {
                type: 'category',
                data: data.map(d => d.name),
                axisLabel: {
                    color: CustomColors.UIGrey800,
                    fontSize: 12
                }
            },
            series: [
                {
                    name: 'ARR',
                    type: 'bar',
                    data: data.map(d => ({
                        value: d.value,
                        percentage: d.percentage
                    })),
                    itemStyle: {
                        color: CustomColors.DeepSkyBlue
                    },
                    label: {
                        show: true,
                        position: 'left',
                        formatter: params => formatCurrency(params.value)
                    }
                }
            ]
        };
    };

    // Get specific metrics
    const totalCustomers = findMetric('total_customers');
    const activeCustomers = findMetric('active_customers');
    const avgArrPerCustomer = findMetric('avg_arr_per_customer');
    const revenueConcentration = findMetric('revenue_concentration');

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Paper elevation={1}
                   sx={{ p: 3, mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom>
                        Customer Dashboard
                    </Typography>
                    <Typography variant="body" color="text.secondary" gutterBottom>
                        Key customer metrics as of {new Date(customerData[0]?.snapshot_date || new Date()).toLocaleDateString('en-AU', { year: 'numeric', month: 'long', day: 'numeric' })}
                    </Typography>
                </Box>
                <Button  startIcon={<ArrowBackIcon fontSize="small" />}
                         onClick={() => navigate('/dashboard')}
                         sx={{
                             fontSize: '0.725rem',
                             px: 1,
                             py: 0.25,
                             minWidth: 'unset',
                             borderRadius: '20px',
                             border: '1px solid',
                             borderColor: CustomColors.DeepSkyBlue,
                             color: CustomColors.DeepSkyBlue,
                             '&:hover': {
                                 backgroundColor: `${CustomColors.DeepSkyBlue}10`
                             }
                         }}>
                    Main Dashboard
                </Button>
            </Paper>

            {/* Top row: Key metrics */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: CustomColors.MidnightBlue, color: 'white' }}>
                        <CardContent>
                            <Typography variant="h7" gutterBottom>
                                ACTIVE CUSTOMERS
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>
                                {activeCustomers.count || 0}
                            </Typography>
                            <Typography variant="bodySmall">
                                {formatPercentage(activeCustomers.percentage)} of all customers
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                TOTAL CUSTOMERS
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.DeepSkyBlue }}>
                                {totalCustomers.count || 0}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Ever created in the system
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                AVG ARR PER CUSTOMER
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Meadow }}>
                                {formatCurrency(avgArrPerCustomer.value_aud)}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Annual recurring revenue
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                TOP 10 REVENUE %
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Purple }}>
                                {formatPercentage(revenueConcentration.percentage)}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Of total ARR
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Charts row */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
                        <Box sx={{ height: 400 }}>
                            <EChartsComponent option={getCustomerTrendOptions()} />
                        </Box>
                    </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
                        <Box sx={{ height: 400 }}>
                            <EChartsComponent option={getCustomerConcentrationOptions()} />
                        </Box>
                    </Paper>
                </Grid>
            </Grid>

            {/* Top customers table */}
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h5" gutterBottom>Top Customers by ARR</Typography>
                <Divider sx={{ mb: 2 }} />
                <Table>
                    <TableHead>
                        <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                            <TableCell sx={{ fontWeight: 'bold' }}>Rank</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Customer</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>ARR</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>% of Total ARR</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Active Contracts</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {topCustomers.map((customer) => (
                            <TableRow key={customer.id} hover>
                                <TableCell>{customer.rank}</TableCell>
                                <TableCell>{customer.label}</TableCell>
                                <TableCell align="right">{formatCurrency(customer.value_aud)}</TableCell>
                                <TableCell align="right">{formatPercentage(customer.percentage)}</TableCell>
                                <TableCell align="right">{customer.count}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </Paper>

            {/* Additional customer metrics */}
            <Paper elevation={1} sx={{ p: 3 }}>
                <Typography variant="h5" gutterBottom>Additional Metrics</Typography>
                <Divider sx={{ mb: 2 }} />
                <Grid container spacing={3}>
                    {[
                        { metricType: 'active_contracts', label: 'Active Contracts' },
                        { metricType: 'new_customers', label: 'New Customers This Month' },
                        { metricType: 'avg_users_per_customer', label: 'Avg Users Per Company' },
                        { metricType: 'avg_active_subscriptions_per_customer', label: 'Avg Contracts Per Customer' }
                    ].map((metric) => {
                        const data = findMetric(metric.metricType);
                        return (
                            <Grid item xs={12} sm={6} md={3} key={metric.metricType}>
                                <Card sx={{ height: '100%' }}>
                                    <CardContent>
                                        <Typography variant="h6" gutterBottom>
                                            {metric.label}
                                        </Typography>
                                        <Typography variant="h4" sx={{ color: CustomColors.UIGrey800 }}>
                                            {data.count !== null && data.count !== undefined ? data.count : '-'}
                                        </Typography>
                                        {data.percentage && (
                                            <Typography variant="body2" color="text.secondary">
                                                {formatPercentage(data.percentage)}
                                            </Typography>
                                        )}
                                    </CardContent>
                                </Card>
                            </Grid>
                        );
                    })}
                </Grid>
            </Paper>
        </Container>
    );
};

export default CustomerDashboard;