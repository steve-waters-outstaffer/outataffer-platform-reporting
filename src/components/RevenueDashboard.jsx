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
    TableCell
} from '@mui/material';
import * as echarts from 'echarts';
import EChartsComponent from './Chart'; // or wherever Chart.jsx is located
import { CustomColors } from '../theme';


const RevenueDashboard = () => {
    const [subscriptionData, setSubscriptionData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Fetch the latest subscription data from your API
        const fetchData = async () => {
            try {
                setLoading(true);

                // This would be replaced with an actual API call to fetch the data
                // from your backend which would query BigQuery
                //
                // const response = await fetch('/api/dashboard/subscription-metrics');
                // const data = await response.json();

                // For now, we'll use the actual data you provided from your BigQuery table
                const data = {
                    "snapshot_date": "2025-03-31",
                    "total_active_subscriptions": 124,
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

                setSubscriptionData(data);
                setLoading(false);
            } catch (err) {
                setError("Failed to load dashboard data");
                setLoading(false);
                console.error("Error fetching dashboard data:", err);
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

    // Revenue trend chart options - Placeholder for future time series data
    const getRevenueTrendOptions = () => {
        const months = ['Jan', 'Feb', 'Mar', 'Apr'];
        const currentMonthIndex = 2; // Mar (index 0-based)
        const mrrValues = [62000, 66000, 81420, null]; // Last value = snapshot, Apr = future

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
                    data: mrrValues,
                    symbol: 'circle',
                    symbolSize: (value, params) => (params.dataIndex === 2 ? 10 : 6),
                    lineStyle: {
                        color: CustomColors.UIGrey400,
                        width: 2
                    },
                    itemStyle: {
                        color: (params) => {
                            return params.dataIndex === 2
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
        const months = ['Jan', 'Feb', 'Mar', 'Apr'];
        const currentMonthIndex = 2; // Mar (index 0-based)
        const subsValues = [105, 118, 124, null]; // Last value = snapshot, Apr = future

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
                    data: subsValues,
                    symbol: 'circle',
                    symbolSize: (value, params) => (params.dataIndex === 2 ? 10 : 6),
                    lineStyle: {
                        color: CustomColors.UIGrey400,
                        width: 2
                    },
                    itemStyle: {
                        color: (params) => {
                            return params.dataIndex === 2
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
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <Typography variant="h5" color="error">{error}</Typography>
            </Box>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h4" component="h1" gutterBottom>
                    Revenue Dashboard
                </Typography>
                <Typography variant="body" color="text.secondary" gutterBottom>
                    Key revenue metrics as of {new Date(subscriptionData.snapshot_date).toLocaleDateString('en-AU', { year: 'numeric', month: 'long', day: 'numeric' })}
                </Typography>
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
                                {subscriptionData.addon_revenue_percentage}% from add-ons
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
                                {subscriptionData.retention_rate}% retention rate
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            <Typography variant="bodySmall" align="center" color="text.secondary" sx={{ mt: 1, mb: 4 }}>
                Chart data will be populated with historical values as more data accumulates
            </Typography>

            {/* Middle row: Revenue trend charts - Placeholder for future time series data */}
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

            {/* Revenue breakdown table */}
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h5" gutterBottom>Monthly Revenue Summary</Typography>
                <Divider sx={{ mb: 2 }} />

                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Revenue Type</TableCell>
                            <TableCell align="right">Amount</TableCell>
                            <TableCell align="right">% of Monthly Revenue</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {/* Recurring */}
                        <TableRow>
                            <TableCell>EOR Fees</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.eor_fees_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage(subscriptionData.eor_fees_mrr / subscriptionData.total_monthly_revenue * 100)}
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableCell>Device Fees</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.device_fees_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage(subscriptionData.device_fees_mrr / subscriptionData.total_monthly_revenue * 100)}
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableCell>Health Insurance</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.health_insurance_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage(subscriptionData.health_insurance_mrr / subscriptionData.total_monthly_revenue * 100)}
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableCell>Hardware Fees</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.hardware_fees_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage(subscriptionData.hardware_fees_mrr / subscriptionData.total_monthly_revenue * 100)}
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableCell>Software Fees</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.software_fees_mrr)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage(subscriptionData.software_fees_mrr / subscriptionData.total_monthly_revenue * 100)}
                            </TableCell>
                        </TableRow>

                        {/* Subtotal Recurring */}
                        <TableRow sx={{ backgroundColor: CustomColors.UIGrey100 }}>
                            <TableCell><strong>Subtotal (Recurring MRR)</strong></TableCell>
                            <TableCell align="right"><strong>{formatCurrency(subscriptionData.total_mrr)}</strong></TableCell>
                            <TableCell align="right"><strong>
                                {formatPercentage(subscriptionData.total_mrr / subscriptionData.total_monthly_revenue * 100)}
                            </strong></TableCell>
                        </TableRow>

                        {/* One-time */}
                        <TableRow>
                            <TableCell>Placement Fees (One-time)</TableCell>
                            <TableCell align="right">{formatCurrency(subscriptionData.placement_fees_monthly)}</TableCell>
                            <TableCell align="right">
                                {formatPercentage(subscriptionData.placement_fees_monthly / subscriptionData.total_monthly_revenue * 100)}
                            </TableCell>
                        </TableRow>

                        {/* Grand Total */}
                        <TableRow sx={{ backgroundColor: CustomColors.UIGrey100 }}>
                            <TableCell><strong>Total Monthly Revenue</strong></TableCell>
                            <TableCell align="right"><strong>{formatCurrency(subscriptionData.total_monthly_revenue)}</strong></TableCell>
                            <TableCell align="right"><strong>100%</strong></TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </Paper>



            {/* Hardware assets */}
            <Paper elevation={1} sx={{ p: 3 }}>
                <Typography variant="h5" gutterBottom>Hardware Assets</Typography>
                <Divider sx={{ mb: 2 }} />

                <Grid container spacing={4}>
                    <Grid item xs={12} md={6}>
                        <Box sx={{ p: 2, border: `1px solid ${CustomColors.UIGrey300}`, borderRadius: 1 }}>
                            <Typography variant="bodySmall" color="text.secondary">Laptops</Typography>
                            <Typography variant="h3" gutterBottom>{subscriptionData.laptops_count}</Typography>
                        </Box>
                    </Grid>
                    <Grid item xs={12} md={6}>
                        <Box sx={{ p: 2, border: `1px solid ${CustomColors.UIGrey300}`, borderRadius: 1 }}>
                            <Typography variant="bodySmall" color="text.secondary">Contracts with Dependents</Typography>
                            <Typography variant="h3" gutterBottom>{subscriptionData.contracts_with_dependents}</Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Avg. {subscriptionData.avg_dependents_per_contract.toFixed(1)} dependents per contract
                            </Typography>
                        </Box>
                    </Grid>
                </Grid>
            </Paper>
        </Container>
    );
};

export default RevenueDashboard;