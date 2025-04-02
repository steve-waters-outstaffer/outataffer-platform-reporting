// src/components/HealthInsuranceDashboard.jsx
import React, { useState, useEffect } from 'react';
import {
    Box,
    Grid,
    Paper,
    Typography,
    CircularProgress,
    Container,
    Table,
    TableHead,
    TableBody,
    TableRow,
    TableCell,
    Divider,
    Card,
    CardContent,
    Alert
} from '@mui/material';
import { CustomColors } from '../theme';
import { fetchLatestHealthInsuranceMetrics } from '../services/ApiService';
import EChartsComponent from './Chart';

const HealthInsuranceDashboard = () => {
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await fetchLatestHealthInsuranceMetrics();
                setHealthData(data);
                setLoading(false);
            } catch (err) {
                console.error('Error fetching health insurance metrics:', err);
                setError('Failed to load health insurance metrics');
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const formatPercentage = (value) => `${parseFloat(value).toFixed(1)}%`;

    // Insurance plan distribution pie chart
    const getInsurancePlanChartOptions = () => {
        const entries = groupedData['health_insurance_plan'];
        if (!entries) return {};

        // Filter out plans with zero contracts
        const plansWithData = entries.filter(plan => Number(plan.count) > 0);

        return {
            title: {
                text: 'Health Insurance Plan Distribution',
                left: 'center',
                textStyle: { color: CustomColors.UIGrey800 }
            },
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                left: 'left',
                data: plansWithData.map(item => item.label)
            },
            series: [
                {
                    name: 'Insurance Plans',
                    type: 'pie',
                    radius: ['50%', '70%'],
                    avoidLabelOverlap: false,
                    label: {
                        show: true,
                        formatter: '{b}: {c} ({d}%)'
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: '16',
                            fontWeight: 'bold'
                        }
                    },
                    labelLine: {
                        show: true
                    },
                    data: plansWithData.map(item => ({
                        value: Number(item.count),
                        name: item.label
                    }))
                }
            ]
        };
    };

    // Group data by metric type and ensure all numeric values are properly converted
    const groupedData = healthData
        ? healthData.reduce((acc, item) => {
            // Convert string values to appropriate types
            const processedItem = {
                ...item,
                count: item.count !== null ? Number(item.count) : 0,
                overall_percentage: item.overall_percentage !== null ? Number(item.overall_percentage) : 0,
                category_percentage: item.category_percentage !== null ? Number(item.category_percentage) : 0,
                contract_count: item.contract_count !== null ? Number(item.contract_count) : 0,
                value: item.value !== null ? Number(item.value) : null
            };

            const category = item.metric_type;
            if (!acc[category]) acc[category] = [];
            acc[category].push(processedItem);
            return acc;
        }, {})
        : {};

    // Helper to find a specific metric by ID
    const findMetric = (metricType, id) => {
        if (!groupedData[metricType]) return null;
        return groupedData[metricType].find(item => item.id === id);
    };

    // Get health insurance coverage rate
    const hasInsuranceMetric = findMetric('has_health_insurance', 'HAS_INSURANCE');
    const coverageRate = hasInsuranceMetric ? parseFloat(hasInsuranceMetric.overall_percentage) : 0;

    // Get dependent metrics
    const hasDependentsMetric = findMetric('health_insurance_dependents', 'HAS_DEPENDENTS');
    const totalDependentsMetric = findMetric('health_insurance_dependents', 'TOTAL_DEPENDENTS');
    const avgDependentsMetric = findMetric('health_insurance_dependents', 'AVG_DEPENDENTS');

    // Dependent distribution chart
    const getDependentsChartOptions = () => {
        if (!hasDependentsMetric || !totalWithInsurance) return {};

        const withDependents = Number(hasDependentsMetric.count);
        const withoutDependents = totalWithInsurance - withDependents;

        return {
            title: {
                text: 'Contracts with Dependents',
                left: 'center',
                textStyle: { color: CustomColors.UIGrey800 }
            },
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                left: 'left',
                data: ['With Dependents', 'Without Dependents']
            },
            color: [CustomColors.SlateBlue, CustomColors.LightGrey],
            series: [
                {
                    name: 'Dependent Status',
                    type: 'pie',
                    radius: '55%',
                    center: ['50%', '60%'],
                    data: [
                        { value: withDependents, name: 'With Dependents' },
                        { value: withoutDependents, name: 'Without Dependents' }
                    ],
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    },
                    label: {
                        formatter: '{b}: {c} ({d}%)'
                    }
                }
            ]
        };
    };

    // Headline metrics
    const totalWithInsurance = hasInsuranceMetric ? Number(hasInsuranceMetric.count) : 0;
    const totalDependents = totalDependentsMetric ? Number(totalDependentsMetric.count) : 0;
    const avgDependentsPerContract = avgDependentsMetric && avgDependentsMetric.value ? Number(avgDependentsMetric.value) : 0;
    const dependentCoverage = hasDependentsMetric ? Number(hasDependentsMetric.category_percentage) : 0;

    // Country distribution for chart
    const getCountryChartOptions = () => {
        const entries = groupedData['health_insurance_by_country'];
        if (!entries) return {};

        const sorted = [...entries].sort((a, b) => Number(b.count) - Number(a.count)).slice(0, 10).reverse();

        return {
            title: {
                text: 'Health Insurance by Country',
                left: 'center',
                textStyle: { color: CustomColors.UIGrey800 }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
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
                    formatter: (value) => `${value}`
                }
            },
            yAxis: {
                type: 'category',
                data: sorted.map((item) => item.label),
                axisLabel: {
                    color: CustomColors.UIGrey700
                }
            },
            series: [
                {
                    name: 'Contracts',
                    type: 'bar',
                    data: sorted.map((item) => Number(item.count)),
                    itemStyle: {
                        color: CustomColors.Cobalt
                    },
                    label: {
                        show: true,
                        position: 'right'
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
                    Health Insurance Analytics
                </Typography>
                <Typography variant="body" color="text.secondary" gutterBottom>
                    Health insurance coverage and dependents as of {healthData?.[0]?.snapshot_date || 'latest'}
                </Typography>
            </Paper>

            {/* Top row: Key metrics */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: CustomColors.Cobalt, color: 'white' }}>
                        <CardContent>
                            <Typography variant="h7" gutterBottom>
                                HEALTH INSURANCE COVERAGE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>
                                {formatPercentage(coverageRate)}
                            </Typography>
                            <Typography variant="bodySmall">
                                {totalWithInsurance} contracts with insurance
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                CONTRACTS WITH DEPENDENTS
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.SlateBlue }}>
                                {formatPercentage(dependentCoverage)}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                {hasDependentsMetric?.count || 0} contracts have dependents
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                TOTAL DEPENDENTS
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Meadow }}>
                                {totalDependents}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Across all insurance plans
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                AVG DEPENDENTS PER CONTRACT
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Purple }}>
                                {avgDependentsPerContract.toFixed(1)}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                For contracts with dependents
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Country distribution chart */}
            {groupedData['health_insurance_by_country'] && (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                    <Typography variant="h5" gutterBottom>Country Distribution</Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Box sx={{ height: 400 }}>
                        <EChartsComponent option={getCountryChartOptions()} />
                    </Box>
                </Paper>
            )}

            {/* Health Insurance Plans Section with Chart and Table */}
            {groupedData['health_insurance_plan'] && (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                    <Typography variant="h5" gutterBottom>Health Insurance Plans</Typography>
                    <Divider sx={{ mb: 2 }} />

                    {/* Add pie chart */}
                    <Box sx={{ height: 400, mb: 3 }}>
                        <EChartsComponent option={getInsurancePlanChartOptions()} />
                    </Box>

                    <Table>
                        <TableHead>
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                <TableCell sx={{ fontWeight: 'bold', width: '40%' }}>Plan</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>Contracts</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>% of Total</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>% with Insurance</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {groupedData['health_insurance_plan']
                                .sort((a, b) => Number(b.count) - Number(a.count))
                                .map((item) => (
                                    <TableRow key={item.id} sx={{ opacity: Number(item.count) > 0 ? 1 : 0.5 }}>
                                        <TableCell sx={{ width: '40%' }}>{item.label}</TableCell>
                                        <TableCell align="right" sx={{ width: '20%' }}>{item.count}</TableCell>
                                        <TableCell align="right" sx={{ width: '20%' }}>{formatPercentage(item.overall_percentage)}</TableCell>
                                        <TableCell align="right" sx={{ width: '20%' }}>{formatPercentage(Number(item.count) / totalWithInsurance * 100)}</TableCell>
                                    </TableRow>
                                ))}
                            {/* Totals row */}
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey100 }}>
                                <TableCell sx={{ fontWeight: 'bold' }}>Total</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                    {totalWithInsurance}
                                </TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                    {formatPercentage(100)}
                                </TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                    {formatPercentage(100)}
                                </TableCell>
                            </TableRow>
                        </TableBody>
                    </Table>
                </Paper>
            )}

            {/* Countries Table */}
            {groupedData['health_insurance_by_country'] && (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                    <Typography variant="h5" gutterBottom>Geographic Distribution</Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Table>
                        <TableHead>
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                <TableCell sx={{ fontWeight: 'bold', width: '40%' }}>Country</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>Contracts</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>% of Total</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>% with Insurance</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {groupedData['health_insurance_by_country']
                                .sort((a, b) => Number(b.count) - Number(a.count))
                                .map((item) => (
                                    <TableRow key={item.id}>
                                        <TableCell sx={{ width: '40%' }}>{item.label}</TableCell>
                                        <TableCell align="right" sx={{ width: '20%' }}>{item.count}</TableCell>
                                        <TableCell align="right" sx={{ width: '20%' }}>{formatPercentage(item.overall_percentage)}</TableCell>
                                        <TableCell align="right" sx={{ width: '20%' }}>{formatPercentage(item.category_percentage)}</TableCell>
                                    </TableRow>
                                ))}
                            {/* Totals row */}
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey100 }}>
                                <TableCell sx={{ fontWeight: 'bold' }}>Total</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                    {groupedData['health_insurance_by_country'].reduce((sum, item) => sum + Number(item.count), 0)}
                                </TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                    {formatPercentage(100)}
                                </TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                    {formatPercentage(100)}
                                </TableCell>
                            </TableRow>
                        </TableBody>
                    </Table>
                </Paper>
            )}

            {/* Dependents Section */}
            {groupedData['health_insurance_dependents'] && (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                    <Typography variant="h5" gutterBottom>Dependents</Typography>
                    <Divider sx={{ mb: 2 }} />

                    <Grid container spacing={3} sx={{ mb: 3 }}>
                        <Grid item xs={12} md={6}>
                            {/* Pie chart for dependents distribution */}
                            <Box sx={{ height: 350 }}>
                                <EChartsComponent option={getDependentsChartOptions()} />
                            </Box>
                        </Grid>

                        <Grid item xs={12} md={6}>
                            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                                <CardContent>
                                    <Typography variant="h6" gutterBottom>
                                        Dependents Summary
                                    </Typography>
                                    <Box sx={{ mt: 2 }}>
                                        <Grid container spacing={2}>
                                            <Grid item xs={8}>
                                                <Typography variant="body">Total Dependents:</Typography>
                                            </Grid>
                                            <Grid item xs={4}>
                                                <Typography variant="body" sx={{ fontWeight: 'bold' }}>
                                                    {totalDependents}
                                                </Typography>
                                            </Grid>

                                            <Grid item xs={8}>
                                                <Typography variant="body">Contracts with Dependents:</Typography>
                                            </Grid>
                                            <Grid item xs={4}>
                                                <Typography variant="body" sx={{ fontWeight: 'bold' }}>
                                                    {hasDependentsMetric?.count || 0}
                                                </Typography>
                                            </Grid>

                                            <Grid item xs={8}>
                                                <Typography variant="body">% of Contracts with Dependents:</Typography>
                                            </Grid>
                                            <Grid item xs={4}>
                                                <Typography variant="body" sx={{ fontWeight: 'bold' }}>
                                                    {formatPercentage(dependentCoverage)}
                                                </Typography>
                                            </Grid>

                                            <Grid item xs={8}>
                                                <Typography variant="body">Average Dependents per Contract:</Typography>
                                            </Grid>
                                            <Grid item xs={4}>
                                                <Typography variant="body" sx={{ fontWeight: 'bold' }}>
                                                    {avgDependentsPerContract.toFixed(2)}
                                                </Typography>
                                            </Grid>

                                            <Grid item xs={8}>
                                                <Typography variant="body">Contracts without Dependents:</Typography>
                                            </Grid>
                                            <Grid item xs={4}>
                                                <Typography variant="body" sx={{ fontWeight: 'bold' }}>
                                                    {totalWithInsurance - Number(hasDependentsMetric?.count || 0)}
                                                </Typography>
                                            </Grid>
                                        </Grid>
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                    </Grid>
                </Paper>
            )}
        </Container>
    );
};

export default HealthInsuranceDashboard;