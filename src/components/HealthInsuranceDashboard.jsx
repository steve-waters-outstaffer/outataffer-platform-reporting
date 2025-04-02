// src/components/HealthInsuranceDashboard.jsx
// Created based on the updated health insurance data structure with country breakdowns
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
    Tabs,
    Tab
} from '@mui/material';
import * as echarts from 'echarts';
import EChartsComponent from './Chart';
import { CustomColors } from '../theme';
import { fetchLatestHealthInsuranceMetrics } from '../services/ApiService';

const HealthInsuranceDashboard = () => {
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeCountryTab, setActiveCountryTab] = useState(0);
    const [groupedData, setGroupedData] = useState({});
    const [countries, setCountries] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                const data = await fetchLatestHealthInsuranceMetrics();
                setHealthData(data);

                // Process and group the data
                const grouped = processHealthData(data);
                setGroupedData(grouped);

                // Extract countries for tabs
                const countryList = Object.keys(grouped.countrySummary || {}).sort();
                setCountries(countryList);

                setLoading(false);
            } catch (err) {
                console.error("Error fetching health insurance data:", err);
                setError("Failed to load health insurance data. Please try again later.");
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    // Process and organize the data for easier access
    const processHealthData = (data) => {
        if (!data || !Array.isArray(data) || data.length === 0) return {};

        const snapshot_date = data[0]?.snapshot_date;
        const result = {
            snapshot_date,
            plansByCountry: {},
            countrySummary: {},
            overall: {},
            dependentsByCountry: {}
        };

        // Group data by metric type and organize
        data.forEach(item => {
            const country = item.id; // For country-specific metrics

            if (item.metric_type === 'health_insurance_plan_by_country') {
                // Extract country from label: "Plan Name (Country Code)"
                const planCountryMatch = item.label.match(/\((.*?)\)$/);
                const planCountry = planCountryMatch ? planCountryMatch[1] : 'Unknown';

                if (!result.plansByCountry[planCountry]) {
                    result.plansByCountry[planCountry] = [];
                }
                result.plansByCountry[planCountry].push(item);
            }
            else if (item.metric_type === 'health_insurance_total_by_country') {
                if (!result.countrySummary[country]) {
                    result.countrySummary[country] = {};
                }
                result.countrySummary[country].totalWithInsurance = parseInt(item.count);
                result.countrySummary[country].coveragePercentage = parseFloat(item.overall_percentage);
            }
            else if (item.metric_type === 'eligible_contracts_by_country') {
                if (!result.countrySummary[country]) {
                    result.countrySummary[country] = {};
                }
                result.countrySummary[country].totalEligible = parseInt(item.count);
            }
            else if (item.metric_type === 'health_insurance_dependents_by_country') {
                result.dependentsByCountry[country] = {
                    count: parseInt(item.count),
                    percentage: parseFloat(item.overall_percentage),
                    contractCount: parseInt(item.contract_count)
                };
            }
        });

        // Calculate overall metrics
        let totalEligible = 0;
        let totalWithInsurance = 0;
        let totalDependents = 0;

        Object.keys(result.countrySummary).forEach(country => {
            const summary = result.countrySummary[country];
            totalEligible += summary.totalEligible || 0;
            totalWithInsurance += summary.totalWithInsurance || 0;
        });

        Object.keys(result.dependentsByCountry).forEach(country => {
            totalDependents += result.dependentsByCountry[country].count || 0;
        });

        // Calculate overall coverage percentage
        const overallCoveragePercentage = totalEligible > 0
            ? (totalWithInsurance / totalEligible * 100)
            : 0;

        // Find country with highest coverage
        let topCoverageCountry = null;
        let topCoveragePercentage = 0;

        Object.keys(result.countrySummary).forEach(country => {
            const summary = result.countrySummary[country];
            if (summary.coveragePercentage > topCoveragePercentage && summary.totalEligible > 0) {
                topCoveragePercentage = summary.coveragePercentage;
                topCoverageCountry = country;
            }
        });

        // Store overall metrics
        result.overall = {
            totalEligible,
            totalWithInsurance,
            overallCoveragePercentage,
            totalDependents,
            topCoverageCountry,
            topCoveragePercentage
        };

        return result;
    };

    // Format percentage values
    const formatPercentage = (value) => {
        if (value === undefined || value === null) return '0.0%';
        return `${value.toFixed(1)}%`;
    };

    // Handle tab change
    const handleTabChange = (event, newValue) => {
        setActiveCountryTab(newValue);
    };

    // Get pie chart options for a specific country
    const getCountryPlanChartOptions = (country) => {
        const plans = groupedData.plansByCountry[country] || [];

        return {
            title: {
                text: `${country} Health Insurance Plans`,
                left: 'center',
                textStyle: {
                    color: CustomColors.UIGrey800
                }
            },
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                left: 'left',
                textStyle: {
                    color: CustomColors.UIGrey700
                }
            },
            series: [
                {
                    name: 'Insurance Plans',
                    type: 'pie',
                    radius: '70%',
                    center: ['50%', '50%'],
                    data: plans.map(plan => ({
                        name: plan.label.replace(` (${country})`, ''),
                        value: parseInt(plan.count)
                    })),
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    },
                    itemStyle: {
                        color: (params) => {
                            const colors = [
                                CustomColors.DeepSkyBlue,
                                CustomColors.MidnightBlue,
                                CustomColors.Meadow,
                                CustomColors.Purple,
                                CustomColors.Pumpkin
                            ];
                            return colors[params.dataIndex % colors.length];
                        }
                    }
                }
            ]
        };
    };

    // Get combined countries bar chart
    const getCountriesComparisonChartOptions = () => {
        const summaryData = groupedData.countrySummary || {};
        const countries = Object.keys(summaryData).sort();

        return {
            title: {
                text: 'Coverage by Country',
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
                    return `${data.name}: ${formatPercentage(data.value)}`;
                }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: countries,
                axisLabel: {
                    color: CustomColors.UIGrey700
                }
            },
            yAxis: {
                type: 'value',
                max: 100,
                axisLabel: {
                    formatter: (value) => `${value}%`,
                    color: CustomColors.UIGrey700
                }
            },
            series: [
                {
                    name: 'Coverage',
                    type: 'bar',
                    data: countries.map(country => {
                        return {
                            value: summaryData[country].coveragePercentage,
                            itemStyle: {
                                color: summaryData[country].coveragePercentage === 100
                                    ? CustomColors.SecretGarden
                                    : CustomColors.DeepSkyBlue
                            }
                        };
                    }),
                    label: {
                        show: true,
                        position: 'top',
                        formatter: '{c}%'
                    }
                }
            ]
        };
    };

    // Get gauge chart options for overall coverage
    const getCoverageGaugeOptions = () => {
        const coverage = groupedData.overall?.overallCoveragePercentage || 0;

        return {
            series: [
                {
                    type: 'gauge',
                    startAngle: 180,
                    endAngle: 0,
                    center: ['50%', '75%'],
                    radius: '100%',
                    min: 0,
                    max: 100,
                    splitNumber: 10,
                    axisLine: {
                        lineStyle: {
                            width: 15,
                            color: [
                                [0.6, CustomColors.DarkRed],
                                [0.8, CustomColors.Pumpkin],
                                [1, CustomColors.SecretGarden]
                            ]
                        }
                    },
                    pointer: {
                        icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                        length: '12%',
                        width: 8,
                        offsetCenter: [0, '-60%'],
                        itemStyle: {
                            color: CustomColors.UIGrey800
                        }
                    },
                    axisTick: {
                        length: 6,
                        distance: -15,
                        lineStyle: {
                            color: '#fff',
                            width: 2
                        }
                    },
                    splitLine: {
                        length: 10,
                        distance: -15,
                        lineStyle: {
                            color: '#fff',
                            width: 2
                        }
                    },
                    axisLabel: {
                        distance: -35,
                        color: CustomColors.UIGrey700,
                        fontSize: 10
                    },
                    detail: {
                        valueAnimation: true,
                        formatter: '{value}%',
                        color: CustomColors.MidnightBlue,
                        fontWeight: 'bold',
                        fontSize: 22,
                        offsetCenter: [0, '-10%']
                    },
                    data: [
                        {
                            value: coverage.toFixed(1),
                            name: 'Coverage'
                        }
                    ]
                }
            ]
        };
    };

    // Get dependent usage chart
    const getDependentsChartOptions = () => {
        const dependentsData = groupedData.dependentsByCountry || {};
        const countries = Object.keys(dependentsData).sort();

        const data = countries.map(country => {
            const countryData = dependentsData[country];
            return {
                name: country,
                count: countryData?.count || 0,
                percentage: countryData?.percentage || 0,
                contracts: countryData?.contractCount || 0
            };
        }).sort((a, b) => b.count - a.count);

        return {
            title: {
                text: 'Dependents by Country',
                left: 'center',
                textStyle: {
                    color: CustomColors.UIGrey800
                }
            },
            tooltip: {
                trigger: 'item',
                formatter: (params) => {
                    const item = data.find(d => d.name === params.name);
                    return `${params.name}: ${item.count} dependents<br/>${formatPercentage(item.percentage)} of contracts`;
                }
            },
            series: [
                {
                    name: 'Dependents',
                    type: 'pie',
                    radius: '70%',
                    center: ['50%', '50%'],
                    data: data.map(item => ({
                        name: item.name,
                        value: item.count
                    })),
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    },
                    itemStyle: {
                        color: (params) => {
                            const colors = [
                                CustomColors.DeepSkyBlue,
                                CustomColors.MidnightBlue,
                                CustomColors.Meadow,
                                CustomColors.Purple,
                                CustomColors.Pumpkin
                            ];
                            return colors[params.dataIndex % colors.length];
                        }
                    },
                    label: {
                        formatter: '{b}: {c}'
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

    // If no data is available after loading
    if (!groupedData || !groupedData.snapshot_date) {
        return (
            <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <Alert severity="info" sx={{ mb: 2 }}>
                    No health insurance data is available.
                </Alert>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h4" component="h1" gutterBottom>
                    Health Insurance Dashboard
                </Typography>
                <Typography variant="body" color="text.secondary" gutterBottom>
                    Health insurance metrics as of {new Date(groupedData.snapshot_date).toLocaleDateString('en-AU', { year: 'numeric', month: 'long', day: 'numeric' })}
                </Typography>
            </Paper>

            {/* Top row: Key metrics cards matching Revenue Dashboard styling */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: CustomColors.MidnightBlue, color: 'white' }}>
                        <CardContent>
                            <Typography variant="h7" gutterBottom>
                                OVERALL COVERAGE RATE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>
                                {formatPercentage(groupedData.overall?.overallCoveragePercentage)}
                            </Typography>
                            <Typography variant="bodySmall">
                                {groupedData.overall?.totalWithInsurance} of {groupedData.overall?.totalEligible} eligible contracts
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                TOTAL DEPENDENTS COVERED
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.DeepSkyBlue }}>
                                {groupedData.overall?.totalDependents || 0}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Additional family members covered
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                TOP COVERAGE COUNTRY
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Meadow }}>
                                {groupedData.overall?.topCoverageCountry || 'N/A'}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                {formatPercentage(groupedData.overall?.topCoveragePercentage)} coverage rate
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                COUNTRIES WITH COVERAGE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Purple }}>
                                {Object.keys(groupedData.countrySummary || {}).length}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Countries with health benefits
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Overall charts */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
                        <Typography variant="h6" gutterBottom sx={{ ml: 2, mt: 1 }}>Overall Coverage Rate</Typography>
                        <Box sx={{ height: 300 }}>
                            <EChartsComponent option={getCoverageGaugeOptions()} />
                        </Box>
                    </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
                        <Typography variant="h6" gutterBottom sx={{ ml: 2, mt: 1 }}>Dependent Coverage</Typography>
                        <Box sx={{ height: 300 }}>
                            <EChartsComponent option={getDependentsChartOptions()} />
                        </Box>
                    </Paper>
                </Grid>
            </Grid>

            {/* Countries comparison chart */}
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h5" gutterBottom>Country Comparison</Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ height: 400 }}>
                    <EChartsComponent option={getCountriesComparisonChartOptions()} />
                </Box>
            </Paper>

            {/* Country-specific details with tabs */}
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h5" gutterBottom>Country Details</Typography>
                <Divider sx={{ mb: 2 }} />

                <Tabs
                    value={activeCountryTab}
                    onChange={handleTabChange}
                    variant="scrollable"
                    scrollButtons="auto"
                    sx={{ mb: 3 }}
                >
                    {countries.map((country, index) => (
                        <Tab key={country} label={country} id={`country-tab-${index}`} />
                    ))}
                </Tabs>

                {countries.map((country, index) => (
                    <Box
                        key={country}
                        role="tabpanel"
                        hidden={activeCountryTab !== index}
                        id={`country-tabpanel-${index}`}
                        aria-labelledby={`country-tab-${index}`}
                    >
                        {activeCountryTab === index && (
                            <Grid container spacing={3}>
                                <Grid item xs={12} md={6}>
                                    <Typography variant="h6" gutterBottom>Health Insurance Plans</Typography>
                                    <Table>
                                        <TableHead>
                                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                                <TableCell sx={{ fontWeight: 'bold' }}>Plan</TableCell>
                                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Employees</TableCell>
                                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Percentage</TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {(groupedData.plansByCountry[country] || []).map((plan) => (
                                                <TableRow key={plan.id} hover>
                                                    <TableCell>{plan.label.replace(` (${country})`, '')}</TableCell>
                                                    <TableCell align="right">{plan.count}</TableCell>
                                                    <TableCell align="right">{formatPercentage(parseFloat(plan.category_percentage))}</TableCell>
                                                </TableRow>
                                            ))}
                                            {/* Summary row */}
                                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey100 }}>
                                                <TableCell sx={{ fontWeight: 'bold' }}>Total</TableCell>
                                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                                    {groupedData.countrySummary[country]?.totalWithInsurance || 0}
                                                </TableCell>
                                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                                    {formatPercentage(groupedData.countrySummary[country]?.coveragePercentage)}
                                                </TableCell>
                                            </TableRow>
                                        </TableBody>
                                    </Table>

                                    {/* Dependents info for this country */}
                                    {groupedData.dependentsByCountry[country] && (
                                        <Box sx={{ mt: 3 }}>
                                            <Typography variant="h6" gutterBottom>Dependents Coverage</Typography>
                                            <Table>
                                                <TableHead>
                                                    <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                                        <TableCell sx={{ fontWeight: 'bold' }}>Metric</TableCell>
                                                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>Value</TableCell>
                                                    </TableRow>
                                                </TableHead>
                                                <TableBody>
                                                    <TableRow hover>
                                                        <TableCell>Total Dependents</TableCell>
                                                        <TableCell align="right">{groupedData.dependentsByCountry[country].count}</TableCell>
                                                    </TableRow>
                                                    <TableRow hover>
                                                        <TableCell>Contracts with Dependents</TableCell>
                                                        <TableCell align="right">
                                                            {formatPercentage(groupedData.dependentsByCountry[country].percentage)}
                                                        </TableCell>
                                                    </TableRow>
                                                </TableBody>
                                            </Table>
                                        </Box>
                                    )}
                                </Grid>
                                <Grid item xs={12} md={6}>
                                    <Box sx={{ height: 400 }}>
                                        <EChartsComponent option={getCountryPlanChartOptions(country)} />
                                    </Box>
                                </Grid>
                            </Grid>
                        )}
                    </Box>
                ))}
            </Paper>
        </Container>
    );
};

export default HealthInsuranceDashboard;