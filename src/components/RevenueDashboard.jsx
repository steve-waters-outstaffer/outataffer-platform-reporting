// src/components/RevenueDashboard.jsx
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
    Alert,
    Button
} from '@mui/material';
import * as echarts from 'echarts';
import EChartsComponent from './Chart';
import { CustomColors } from '../theme';
import { fetchLatestRevenueMetrics, fetchRevenueTrend, fetchSubscriptionTrend, checkApiHealth } from '../services/ApiService';
import { useNavigate } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';



const RevenueDashboard = () => {
    const navigate = useNavigate();
    const [subscriptionData, setSubscriptionData] = useState(null);
    const [revenueTrend, setRevenueTrend] = useState([]);
    const [subscriptionTrend, setSubscriptionTrend] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [usingFallback, setUsingFallback] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                // Fetch all data in parallel
                const [metricsData, revTrend, subTrend] = await Promise.all([
                    fetchLatestRevenueMetrics(),
                    fetchRevenueTrend(4), // Last 4 months
                    fetchSubscriptionTrend(4) // Last 4 months
                ]);

                setSubscriptionData(metricsData);
                setRevenueTrend(revTrend);
                setSubscriptionTrend(subTrend);
                setLoading(false);
            } catch (err) {
                console.error("Error fetching dashboard data:", err);
                setError("Failed to load dashboard data. Please try again later.");
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

    // Revenue breakdown chart options
    const getRevenueBreakdownOptions = (data) => {
        if (!data) return {};

        return {
            title: {
                text: 'Monthly Revenue Breakdown',
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
                    return `${data.name}: ${formatCurrency(data.value)}`;
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
                data: ['EOR Fees', 'Device Fees', 'Hardware', 'Software', 'Health Insurance', 'Placement Fees'],
                axisLabel: {
                    color: CustomColors.UIGrey700
                }
            },
            series: [
                {
                    name: 'Revenue',
                    type: 'bar',
                    data: [
                        data.eor_fees_mrr,
                        data.device_fees_mrr,
                        data.hardware_fees_mrr,
                        data.software_fees_mrr,
                        data.health_insurance_mrr,
                        data.placement_fees_monthly
                    ],
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                            { offset: 0, color: CustomColors.DeepSkyBlue },
                            { offset: 1, color: CustomColors.MidnightBlue }
                        ])
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

    // Retention gauge options
    const getRetentionGaugeOptions = (data) => {
        if (!data) return {};

        return {
            title: {
                text: 'Customer Retention',
                left: 'center',
                textStyle: {
                    color: CustomColors.UIGrey800
                }
            },
            tooltip: {
                formatter: '{b}: {c}%'
            },
            series: [
                {
                    name: 'Retention Rate',
                    type: 'gauge',
                    radius: '100%',
                    min: 0,
                    max: 100,
                    splitNumber: 10,
                    axisLine: {
                        lineStyle: {
                            width: 20,
                            color: [
                                [0.7, CustomColors.DarkRed],
                                [0.9, CustomColors.Pumpkin],
                                [1, CustomColors.SecretGarden]
                            ]
                        }
                    },
                    pointer: {
                        itemStyle: {
                            color: CustomColors.UIGrey800
                        },
                        width: 5
                    },
                    axisTick: {
                        distance: -20,
                        length: 8,
                        lineStyle: {
                            color: '#fff',
                            width: 2
                        }
                    },
                    splitLine: {
                        distance: -20,
                        length: 20,
                        lineStyle: {
                            color: '#fff',
                            width: 2
                        }
                    },
                    axisLabel: {
                        distance: -10,
                        color: CustomColors.UIGrey700,
                        fontSize: 12
                    },
                    detail: {
                        valueAnimation: true,
                        formatter: '{value}%',
                        color: CustomColors.MidnightBlue,
                        fontSize: 24,
                        fontWeight: 'bold',
                        offsetCenter: [0, '60%']
                    },
                    data: [
                        {
                            value: data.retention_rate,
                            name: 'Retention'
                        }
                    ]
                }
            ]
        };
    };

    // Revenue composition chart
    const getRevenueCompositionOptions = (data) => {
        if (!data) return {};

        // Calculate addon vs core EOR
        const coreEorRevenue = data.eor_fees_mrr;
        const addonRevenue = data.device_fees_mrr + data.hardware_fees_mrr +
            data.software_fees_mrr + data.health_insurance_mrr;

        return {
            title: {
                text: 'Revenue Composition',
                left: 'center',
                textStyle: {
                    color: CustomColors.UIGrey800
                }
            },
            tooltip: {
                trigger: 'item',
                formatter: (params) => `${params.name}: ${formatCurrency(params.value)} (${params.percent}%)`
            },
            legend: {
                bottom: '0%',
                left: 'center'
            },
            series: [
                {
                    name: 'Revenue',
                    type: 'funnel',
                    left: '10%',
                    top: 60,
                    bottom: 60,
                    width: '80%',
                    min: 0,
                    max: data.total_mrr,
                    minSize: '0%',
                    maxSize: '100%',
                    sort: 'descending',
                    gap: 2,
                    label: {
                        show: true,
                        position: 'inside',
                        formatter: (params) => `${params.name}: ${params.percent}%`
                    },
                    itemStyle: {
                        borderColor: '#fff',
                        borderWidth: 1
                    },
                    emphasis: {
                        label: {
                            fontSize: 16
                        }
                    },
                    data: [
                        { value: coreEorRevenue, name: 'Core EOR', itemStyle: { color: CustomColors.MidnightBlue } },
                        { value: addonRevenue, name: 'Add-ons', itemStyle: { color: CustomColors.DeepSkyBlue } },
                        { value: data.placement_fees_monthly, name: 'One-time Fees', itemStyle: { color: CustomColors.Meadow } }
                    ]
                }
            ]
        };
    };

    // Revenue trend chart options
    const getRevenueTrendOptions = () => {
        // Use the actual API data if available, otherwise use placeholder
        const trendData = revenueTrend.length > 0 ? revenueTrend : [];
        const months = trendData.map(item => item.month);
        const values = trendData.map(item => item.value);

        // Find the latest month index
        const currentMonthIndex = trendData.length - 1;

        return {
            tooltip: {
                trigger: 'axis',
                formatter: params => `${params[0].name}: ${formatCurrency(params[0].value)}`
            },
            grid: {
                left: '10%',
                right: '4%',
                bottom: '15%',
                top: '10%',
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
                axisLabel: {
                    formatter: value => formatCurrency(value)
                }
            },
            series: [
                {
                    name: 'MRR',
                    type: 'line',
                    data: values,
                    symbol: 'circle',
                    symbolSize: (value, params) => (params.dataIndex === currentMonthIndex ? 10 : 6),
                    lineStyle: {
                        color: CustomColors.UIGrey400,
                        width: 2
                    },
                    itemStyle: {
                        color: (params) => {
                            return params.dataIndex === currentMonthIndex
                                ? CustomColors.DeepSkyBlue
                                : CustomColors.UIGrey300;
                        },
                        borderColor: CustomColors.UIGrey600,
                        borderWidth: 1
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(180,180,180,0.15)' },
                            { offset: 1, color: 'rgba(180,180,180,0.02)' }
                        ])
                    }
                }
            ]
        };
    };

    // Active Subscriptions trend chart
    const getActiveSubscriptionsOptions = () => {
        // Use the actual API data if available, otherwise use placeholder
        const trendData = subscriptionTrend.length > 0 ? subscriptionTrend : [];
        const months = trendData.map(item => item.month);
        const values = trendData.map(item => item.value);

        // Find the latest month index
        const currentMonthIndex = trendData.length - 1;

        return {
            tooltip: {
                trigger: 'axis',
                formatter: params => `${params[0].name}: ${params[0].value} subscriptions`
            },
            grid: {
                left: '10%',
                right: '4%',
                bottom: '15%',
                top: '10%',
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
                axisLabel: {
                    formatter: value => value
                }
            },
            series: [
                {
                    name: 'Active Subscriptions',
                    type: 'line',
                    data: values,
                    symbol: 'circle',
                    symbolSize: (value, params) => (params.dataIndex === currentMonthIndex ? 10 : 6),
                    lineStyle: {
                        color: CustomColors.UIGrey400,
                        width: 2
                    },
                    itemStyle: {
                        color: (params) => {
                            return params.dataIndex === currentMonthIndex
                                ? CustomColors.DeepSkyBlue
                                : CustomColors.UIGrey300;
                        },
                        borderColor: CustomColors.UIGrey600,
                        borderWidth: 1
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(180,180,180,0.15)' },
                            { offset: 1, color: 'rgba(180,180,180,0.02)' }
                        ])
                    }
                }
            ]
        };
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <CircularProgress color="secondary" />
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh', flexDirection: 'column', p: 3 }}>
                <Alert severity="error" sx={{ mb: 2, width: '100%', maxWidth: 600 }}>
                    {error}
                </Alert>
                <Typography variant="body">
                    Please check your network connection and API configuration.
                </Typography>
            </Box>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Paper
                elevation={1}
                sx={{ p: 3, mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom>
                        Revenue Dashboard
                    </Typography>
                    <Typography variant="body" color="text.secondary" gutterBottom>
                        Key revenue metrics as of {new Date(subscriptionData.snapshot_date || new Date()).toLocaleDateString('en-AU', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                    })}
                    </Typography>

                    {usingFallback && (
                        <Alert severity="info" sx={{ mt: 2 }}>
                            Using development sample data – API endpoints not yet fully implemented
                        </Alert>
                    )}
                </Box>
                <Button
                    startIcon={<ArrowBackIcon fontSize="small" />}
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
                    }}
                >
                    Main Dashboard
                </Button>
            </Paper>


            {/* Top row: Key metrics */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: CustomColors.MidnightBlue, color: 'white' }}>
                        <CardContent>
                            <Typography variant="h7" gutterBottom>
                                MONTHLY RECURRING REVENUE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>
                                {formatCurrency(subscriptionData.total_mrr)}
                            </Typography>
                            <Typography variant="bodySmall">
                                {subscriptionData.new_subscriptions} new contracts this month
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                ANNUAL RECURRING REVENUE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.DeepSkyBlue }}>
                                {formatCurrency(subscriptionData.total_arr)}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                {(subscriptionData.addon_revenue_percentage || 0).toFixed(1)}% from add-ons
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                ACTIVE SUBSCRIPTIONS
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Meadow }}>
                                {subscriptionData.total_active_subscriptions}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Avg value: {formatCurrency(subscriptionData.avg_subscription_value)}/mo
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
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Purple }}>
                                {subscriptionData.total_customers}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                TO-DO Net change
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {revenueTrend.length === 0 && (
                <Typography variant="bodySmall" align="center" color="text.secondary" sx={{ mt: 1, mb: 4 }}>
                    Chart data will be populated with historical values as more data accumulates
                </Typography>
            )}

            {/* Middle row: Revenue trend charts */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2, mb: 1 }}>
                        <Typography variant="h6" gutterBottom sx={{ ml: 2, mt: 1 }}>Monthly Revenue Trend</Typography>
                        <Box sx={{ height: 380 }}>
                            <EChartsComponent option={getRevenueTrendOptions()} />
                        </Box>

                    </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2, mb: 1 }}>
                        <Typography variant="h6" gutterBottom sx={{ ml: 2, mt: 1 }}>Active Subscriptions</Typography>
                        <Box sx={{ height: 380 }}>
                            <EChartsComponent option={getActiveSubscriptionsOptions()} />
                        </Box>
                    </Paper>
                </Grid>
            </Grid>

            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h4" gutterBottom>Monthly Revenue Summary</Typography>
                <Divider sx={{ mb: 2 }} />

                <Table>
                    <TableHead>
                        <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                            <TableCell sx={{ fontWeight: 'bold' }}>Revenue Type</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Amount</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>% of Monthly Revenue</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {/* Recurring */}
                        <TableRow hover>
                            <TableCell>EOR Fees</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.eor_fees_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage((subscriptionData.eor_fees_mrr || 0) / (subscriptionData.total_monthly_revenue || 1) * 100)}
                            </TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Device Fees</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.device_fees_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage((subscriptionData.device_fees_mrr || 0) / (subscriptionData.total_monthly_revenue || 1) * 100)}
                            </TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Health Insurance</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.health_insurance_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage((subscriptionData.health_insurance_mrr || 0) / (subscriptionData.total_monthly_revenue || 1) * 100)}
                            </TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Hardware Fees</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.hardware_fees_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage((subscriptionData.hardware_fees_mrr || 0) / (subscriptionData.total_monthly_revenue || 1) * 100)}
                            </TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Software Fees</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.software_fees_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage((subscriptionData.software_fees_mrr || 0) / (subscriptionData.total_monthly_revenue || 1) * 100)}
                            </TableCell>
                        </TableRow>

                        {/* Subtotal Recurring */}
                        <TableRow sx={{ backgroundColor: CustomColors.MidnightBlue }}>
                            <TableCell sx={{ fontWeight: 'bold', color: 'white' }}>Subtotal (Recurring MRR)</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>{formatCurrency(subscriptionData.total_mrr)}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>
                                {formatPercentage((subscriptionData.total_mrr || 0) / (subscriptionData.total_monthly_revenue || 1) * 100)}
                            </TableCell>
                        </TableRow>

                        {/* One-time */}
                        <TableRow hover>
                            <TableCell>Placement Fees (One-time)</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.placement_fees_monthly)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage((subscriptionData.placement_fees_monthly || 0) / (subscriptionData.total_monthly_revenue || 1) * 100)}
                            </TableCell>
                        </TableRow>

                        {/* Grand Total */}
                        <TableRow sx={{ backgroundColor: CustomColors.DeepSkyBlue }}>
                            <TableCell sx={{ fontWeight: 'bold', color: 'white' }}>Total Monthly Revenue</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>{formatCurrency(subscriptionData.total_monthly_revenue)}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>100%</TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </Paper>



        </Container>
    );
};

export default RevenueDashboard;