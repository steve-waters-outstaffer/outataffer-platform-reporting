// src/components/RevenueDashboard.jsx
import React, { useState, useEffect } from 'react';
import BetaWatermark from './BetaWatermark';
import {
    Box,
    Grid,
    Paper,
    Typography,
    Card,
    CardContent,
    CircularProgress,
    Container,
    Alert,
    Divider,
    Table,
    TableHead,
    TableBody,
    TableRow,
    TableCell,
    Button, Toolbar, AppBar
} from '@mui/material';
import * as echarts from 'echarts';
import { useAuth } from '../contexts/AuthContext';
import { logoutUser } from '../services/AuthService.js';
import EChartsComponent from './Chart';
import { CustomColors } from '../theme';
import { useNavigate } from 'react-router-dom'; // Imported but needs to be used
import { fetchLatestRevenueMetrics, fetchRevenueTrend, fetchSubscriptionTrend } from '../services/ApiService';
import CountryBreakdown from './CountryBreakdown';
import ArrowBackIcon from "@mui/icons-material/ArrowBack.js";

const RevenueDashboard = () => {
    const navigate = useNavigate(); // Define navigate here
    const [subscriptionData, setSubscriptionData] = useState(null);
    const [revenueTrend, setRevenueTrend] = useState([]);
    const [subscriptionTrend, setSubscriptionTrend] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { currentUser } = useAuth();

    const handleLogout = async () => {
        try {
            await logoutUser();
            navigate('/login');
        } catch (error) {
            console.error("Logout error:", error);
        }
    };
    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                const [metricsData, revTrend, subTrend] = await Promise.all([
                    fetchLatestRevenueMetrics(),
                    fetchRevenueTrend(4),
                    fetchSubscriptionTrend(4)
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

    const formatCurrency = (value) => {
        return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(value);
    };

    const formatPercentage = (value) => `${value.toFixed(1)}%`;

    const getValue = (key, field = 'value_aud') => {
        if (!subscriptionData || !subscriptionData[key]) return 0;
        return subscriptionData[key][field] ?? 0;
    };

    const getRevenueTrendOptions = () => {
        const trendData = revenueTrend.length > 0 ? revenueTrend : [];
        const months = trendData.map(item => item.month);
        const values = trendData.map(item => item.value);
        const currentMonthIndex = trendData.length - 1;

        return {
            tooltip: { trigger: 'axis', formatter: params => `${params[0].name}: ${formatCurrency(params[0].value)}` },
            grid: { left: '10%', right: '15%', bottom: '15%', top: '10%', containLabel: true },
            xAxis: { type: 'category', boundaryGap: false, data: months, axisLabel: { color: CustomColors.UIGrey700, margin: 14 } },
            yAxis: { type: 'value', axisLabel: { formatter: value => formatCurrency(value) } },
            series: [{
                name: 'MRR',
                type: 'line',
                data: values,
                symbol: 'circle',
                symbolSize: (value, params) => (params.dataIndex === currentMonthIndex ? 10 : 6),
                lineStyle: { color: CustomColors.UIGrey400, width: 2 },
                itemStyle: {
                    color: (params) => (params.dataIndex === currentMonthIndex ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300),
                    borderColor: CustomColors.UIGrey600,
                    borderWidth: 1
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(180,180,180,0.15)' },
                        { offset: 1, color: 'rgba(180,180,180,0.02)' }
                    ])
                }
            }]
        };
    };

    const getActiveSubscriptionsOptions = () => {
        const trendData = subscriptionTrend.length > 0 ? subscriptionTrend : [];
        const months = trendData.map(item => item.month);
        const values = trendData.map(item => item.value);
        const currentMonthIndex = trendData.length - 1;

        return {
            tooltip: { trigger: 'axis', formatter: params => `${params[0].name}: ${params[0].value} subscriptions` },
            grid: { left: '10%', right: '15%', bottom: '15%', top: '10%', containLabel: true },
            xAxis: { type: 'category', boundaryGap: false, data: months, axisLabel: { color: CustomColors.UIGrey700, margin: 14 } },
            yAxis: { type: 'value', axisLabel: { formatter: value => value } },
            series: [{
                name: 'Active Subscriptions',
                type: 'line',
                data: values,
                symbol: 'circle',
                symbolSize: (value, params) => (params.dataIndex === currentMonthIndex ? 10 : 6),
                lineStyle: { color: CustomColors.UIGrey400, width: 2 },
                itemStyle: {
                    color: (params) => (params.dataIndex === currentMonthIndex ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300),
                    borderColor: CustomColors.UIGrey600,
                    borderWidth: 1
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(180,180,180,0.15)' },
                        { offset: 1, color: 'rgba(180,180,180,0.02)' }
                    ])
                }
            }]
        };
    };

    if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}><CircularProgress color="secondary" /></Box>;

    if (error) return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh', flexDirection: 'column', p: 3 }}>
            <Alert severity="error" sx={{ mb: 2, width: '100%', maxWidth: 600 }}>{error}</Alert>
            <Typography variant="body">Please check your network connection and API configuration.</Typography>
        </Box>
    );

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: CustomColors.UIGrey100 }}>
        <AppBar position="static" color="secondary">
            <Toolbar>
                <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                    Outstaffer Dashboard
                </Typography>
                <Typography variant="bodySmall" sx={{ mr: 2 }}>
                    {currentUser?.email}
                </Typography>
                <Button
                    variant="outlined"
                    color="default"
                    onClick={handleLogout}
                    size="small"
                >
                    Logout
                </Button>
            </Toolbar>
            <Box sx={{ px: 2, mb: 2 }}>
                <Typography variant="h4" color="text.secondary" align={"center"}>
                    This dashboard is in beta and may display incomplete information, some data may be missing or out of date. Please do not rely on this dashboard for critical decisions or reporting purposes.
                </Typography>
            </Box>
        </AppBar>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <BetaWatermark />
             <Paper elevation={1}
                   sx={{ p: 3, mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" component="h1">Revenue Dashboard</Typography>
                    <Typography variant="body" color="text.secondary">
                        Key revenue metrics as of {new Date(subscriptionData.snapshot_date).toLocaleDateString('en-AU')}
                    </Typography>
                </Box>
                <Button startIcon={<ArrowBackIcon fontSize="small" />}
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
                                MONTHLY RECURRING REVENUE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>
                                {formatCurrency(getValue('total_mrr'))}
                            </Typography>
                            <Typography variant="bodySmall">
                                {getValue('new_subscriptions', 'count')} new contracts this month
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
                                {formatCurrency(getValue('total_arr'))}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                {formatPercentage(getValue('addon_revenue_percentage', 'percentage'))} from add-ons
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
                                {getValue('total_active', 'count')}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Avg value: {formatCurrency(getValue('avg_subscription_value'))}/mo
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
                                {getValue('total_customers', 'count')}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                {getValue('new_customers_this_month', 'count') > 0
                                    ? `+${getValue('new_customers_this_month', 'count')} this month`
                                    : "No change this month"}
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            <Grid container spacing={3} sx={{ mt: 4 }}>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Monthly Revenue Trend</Typography>
                        <Box sx={{ height: 380 }}><EChartsComponent option={getRevenueTrendOptions()} /></Box>
                    </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Active Subscriptions</Typography>
                        <Box sx={{ height: 380 }}><EChartsComponent option={getActiveSubscriptionsOptions()} /></Box>
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
                        <TableRow hover>
                            <TableCell>EOR Fees</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('eor_fees'))}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('eor_fees') / getValue('total_monthly_revenue') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Device Fees</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('device_fees'))}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('device_fees') / getValue('total_monthly_revenue') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Health Insurance</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('health_insurance'))}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('health_insurance') / getValue('total_monthly_revenue') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Hardware Fees</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('hardware_fees'))}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('hardware_fees') / getValue('total_monthly_revenue') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Software Fees</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('software_fees'))}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('software_fees') / getValue('total_monthly_revenue') * 100)}</TableCell>
                        </TableRow>
                        <TableRow sx={{ backgroundColor: CustomColors.MidnightBlue }}>
                            <TableCell sx={{ fontWeight: 'bold', color: 'white' }}>Subtotal (Recurring MRR)</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>{formatCurrency(getValue('total_mrr'))}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>{formatPercentage(getValue('total_mrr') / getValue('total_monthly_revenue') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Placement Fees (One-time)</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('placement_fees'))}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('placement_fees') / getValue('total_monthly_revenue') * 100)}</TableCell>
                        </TableRow>
                        <TableRow sx={{ backgroundColor: CustomColors.DeepSkyBlue }}>
                            <TableCell sx={{ fontWeight: 'bold', color: 'white' }}>Total Monthly Revenue</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>{formatCurrency(getValue('total_monthly_revenue'))}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>100%</TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </Paper>

            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h4" gutterBottom>Annual Recurring Revenue Summary</Typography>
                <Divider sx={{ mb: 2 }} />
                <Table>
                    <TableHead>
                        <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                            <TableCell sx={{ fontWeight: 'bold' }}>Revenue Type</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Amount</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>% of Annual Revenue</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        <TableRow hover>
                            <TableCell>EOR Fees</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('eor_fees') * 12)}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('eor_fees') / getValue('total_mrr') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Device Fees</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('device_fees') * 12)}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('device_fees') / getValue('total_mrr') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Health Insurance</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('health_insurance') * 12)}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('health_insurance') / getValue('total_mrr') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Hardware Fees</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('hardware_fees') * 12)}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('hardware_fees') / getValue('total_mrr') * 100)}</TableCell>
                        </TableRow>
                        <TableRow hover>
                            <TableCell>Software Fees</TableCell>
                            <TableCell align="right">{formatCurrency(getValue('software_fees') * 12)}</TableCell>
                            <TableCell align="right">{formatPercentage(getValue('software_fees') / getValue('total_mrr') * 100)}</TableCell>
                        </TableRow>
                        <TableRow sx={{ backgroundColor: CustomColors.DeepSkyBlue }}>
                            <TableCell sx={{ fontWeight: 'bold', color: 'white' }}>Total Annual Recurring Revenue</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>{formatCurrency(getValue('total_arr'))}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', color: 'white' }}>100%</TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </Paper>

        </Container>
       </Box>
    );
};

export default RevenueDashboard;