// src/components/HealthInsuranceDashboard.jsx
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
    Alert
} from '@mui/material';
import * as echarts from 'echarts';
import EChartsComponent from './Chart';
import { CustomColors } from '../theme';
import { fetchLatestHealthInsuranceMetrics } from '../services/ApiService';

const HealthInsuranceDashboard = () => {
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [processedData, setProcessedData] = useState({
        plansByCountry: {},
        countrySummary: {},
        overall: {},
        dependentsByCountry: {},
        allPlans: [] // Store all unique plan types
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                // Fetch from API with cache-busting query parameter
                const timestamp = new Date().getTime();
                const data = await fetchLatestHealthInsuranceMetrics(`?_=${timestamp}`);
                console.log("API Response Data:", data);
                setHealthData(data);

                // Process the data for easier access
                const processed = processHealthData(data);
                setProcessedData(processed);

                setLoading(false);
            } catch (err) {
                console.error("Error fetching health insurance data:", err);
                setError("Failed to load health insurance data. Please try again later.");
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    // Process and organize the API data for easier access
    const processHealthData = (data) => {
        if (!data || !Array.isArray(data) || data.length === 0) return {};

        const snapshot_date = data[0]?.snapshot_date;
        const result = {
            snapshot_date,
            plansByCountry: {},
            countrySummary: {},
            overall: {},
            dependentsByCountry: {},
            allPlans: [] // Track all unique plans
        };

        // First pass - identify all unique plan IDs
        const uniquePlans = new Set();
        data.forEach(item => {
            if (item.metric_type === 'health_insurance_plan_by_country') {
                uniquePlans.add(item.id);
            }
        });

        // Convert Set to array of objects with names
        const allPlans = Array.from(uniquePlans).map(planId => {
            // Find an item with this plan ID to get its label
            const matchingItem = data.find(
                item => item.metric_type === 'health_insurance_plan_by_country' && item.id === planId
            );

            // Extract the plan name (remove country in parentheses)
            let planName = planId;
            if (matchingItem) {
                const planCountryMatch = matchingItem.label.match(/^(.*?)(?:\s*\(.*?\))?$/);
                planName = planCountryMatch ? planCountryMatch[1] : matchingItem.label;
            }

            return { id: planId, name: planName };
        });

        result.allPlans = allPlans;

        // Group data by metric type and organize
        data.forEach(item => {
            // For metrics with country in the label (health_insurance_plan_by_country)
            if (item.metric_type === 'health_insurance_plan_by_country') {
                // Extract country from label: "Plan Name (Country Code)"
                const planCountryMatch = item.label.match(/\((.*?)\)$/);
                const planCountry = planCountryMatch ? planCountryMatch[1] : 'Unknown';
                const planName = item.label.replace(` (${planCountry})`, '');

                if (!result.plansByCountry[planCountry]) {
                    result.plansByCountry[planCountry] = [];
                }

                result.plansByCountry[planCountry].push({
                    id: item.id,
                    name: planName,
                    count: parseInt(item.count),
                    percentage: parseFloat(item.overall_percentage)
                });
            }
            // For country-level metrics
            else if (item.metric_type === 'health_insurance_total_by_country') {
                const country = item.id; // Country code
                if (!result.countrySummary[country]) {
                    result.countrySummary[country] = {};
                }
                result.countrySummary[country].totalWithInsurance = parseInt(item.count);
                result.countrySummary[country].coveragePercentage = parseFloat(item.overall_percentage);
            }
            else if (item.metric_type === 'eligible_contracts_by_country') {
                const country = item.id; // Country code
                if (!result.countrySummary[country]) {
                    result.countrySummary[country] = {};
                }
                result.countrySummary[country].totalEligible = parseInt(item.count);
            }
            else if (item.metric_type === 'health_insurance_dependents_by_country') {
                const country = item.id; // Country code
                result.dependentsByCountry[country] = {
                    count: parseInt(item.count),
                    percentage: parseFloat(item.overall_percentage),
                    contractCount: parseInt(item.contract_count)
                };
            }
        });

        // Ensure all countries have all plans (even with 0 usage)
        const countries = Object.keys(result.countrySummary);
        countries.forEach(country => {
            // Create a set of plan IDs that already exist for this country
            const existingPlanIds = new Set(
                (result.plansByCountry[country] || []).map(plan => plan.id)
            );

            // Add missing plans with count 0
            allPlans.forEach(plan => {
                if (!existingPlanIds.has(plan.id)) {
                    if (!result.plansByCountry[country]) {
                        result.plansByCountry[country] = [];
                    }

                    result.plansByCountry[country].push({
                        id: plan.id,
                        name: plan.name,
                        count: 0,
                        percentage: 0
                    });
                }
            });
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
            if (summary.coveragePercentage > topCoveragePercentage && summary.totalEligible > 10) {
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
            topCoveragePercentage,
            countriesWithCoverage: Object.keys(result.countrySummary).length
        };

        return result;
    };

    // Format percentage values
    const formatPercentage = (value) => {
        if (value === undefined || value === null) return '0.0%';
        return `${value.toFixed(1)}%`;
    };

    // Get bar chart options for a specific country
    const getCountryBarChartOptions = (country) => {
        const plans = processedData.plansByCountry[country] || [];
        const sortedPlans = [...plans].sort((a, b) => b.count - a.count);

        return {
            title: {
                text: `${country} Health Insurance Plan Distribution`,
                left: 'center',
                top: '5%', // Add padding from the top
                textStyle: {
                    color: CustomColors.UIGrey800,
                    fontSize: 15, // Adjust font size
                    fontWeight: 'normal' // Reduce weight for less emphasis
                }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: (params) => {
                    const data = params[0];
                    return `${data.name}: ${data.value} (${data.value > 0 ? formatPercentage(data.value / processedData.countrySummary[country]?.totalWithInsurance * 100) : '0.0%'})`;
                }
            },
            grid: {
                left: '20%', // Increased to accommodate longer labels
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'value', // Swapped to value for horizontal bars
                axisLabel: {
                    formatter: (value) => value
                }
            },
            yAxis: {
                type: 'category', // Swapped to category for horizontal bars
                data: sortedPlans.map(plan => plan.name),
                axisLabel: {
                    color: CustomColors.UIGrey700,
                    fontSize: 11
                }
            },
            series: [
                {
                    name: 'Employees',
                    type: 'bar',
                    data: sortedPlans.map(plan => ({
                        value: plan.count,
                        itemStyle: {
                            color: plan.count > 0 ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300
                        }
                    })),
                    label: {
                        show: true,
                        position: 'right', // Changed to right for horizontal bars
                        formatter: '{c}'
                    }
                }
            ]
        };
    };

    // Get combined countries bar chart
    const getCountriesComparisonChartOptions = () => {
        const summaryData = processedData.countrySummary || {};
        const countries = Object.keys(summaryData).sort();

        return {
            title: {
                text: 'Insurance Coverage by Country',
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
                    const country = params[0].name;
                    const value = params[0].value;
                    const total = summaryData[country]?.totalEligible || 0;
                    return `${country}: ${value} of ${total} employees (${formatPercentage(params[0].value2)})`;
                }
            },
            grid: {
                left: '20%', // Increased to accommodate longer labels
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'value', // Swapped to value for horizontal bars
                axisLabel: {
                    formatter: (value) => value
                }
            },
            yAxis: {
                type: 'category', // Swapped to category for horizontal bars
                data: countries,
                axisLabel: {
                    color: CustomColors.UIGrey700
                }
            },
            series: [
                {
                    name: 'Employees with Coverage',
                    type: 'bar',
                    data: countries.map(country => ({
                        value: summaryData[country].totalWithInsurance,
                        value2: summaryData[country].coveragePercentage,
                        itemStyle: {
                            color: summaryData[country].coveragePercentage >= 99
                                ? CustomColors.SecretGarden
                                : CustomColors.DeepSkyBlue
                        }
                    })),
                    label: {
                        show: true,
                        position: 'right', // Changed to right for horizontal bars
                        formatter: (params) => {
                            return `${params.value} (${formatPercentage(summaryData[params.name].coveragePercentage)})`;
                        }
                    }
                }
            ]
        };
    };

    // Sort countries by total employees with insurance (descending)
    const sortedCountries = Object.keys(processedData.countrySummary || {})
        .sort((a, b) => {
            const aCount = processedData.countrySummary[a]?.totalWithInsurance || 0;
            const bCount = processedData.countrySummary[b]?.totalWithInsurance || 0;
            return bCount - aCount;
        });

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h4" component="h1" gutterBottom>
                    Health Insurance Dashboard
                </Typography>
                <Typography variant="body" color="text.secondary" gutterBottom>
                    Health insurance metrics as of {new Date(processedData.snapshot_date).toLocaleDateString('en-AU', { year: 'numeric', month: 'long', day: 'numeric' })}
                </Typography>
            </Paper>

            {/* Top row: Key metrics cards */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: CustomColors.MidnightBlue, color: 'white' }}>
                        <CardContent>
                            <Typography variant="h7" gutterBottom>
                                OVERALL COVERAGE RATE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>
                                {formatPercentage(processedData.overall?.overallCoveragePercentage)}
                            </Typography>
                            <Typography variant="bodySmall">
                                {processedData.overall?.totalWithInsurance} of {processedData.overall?.totalEligible} eligible contracts
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                TOTAL COVERED EMPLOYEES
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.DeepSkyBlue }}>
                                {processedData.overall?.totalWithInsurance || 0}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Total employees with insurance
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
                                {processedData.overall?.topCoverageCountry || 'N/A'}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                {formatPercentage(processedData.overall?.topCoveragePercentage)} coverage rate
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                DEPENDENTS COVERED
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Purple }}>
                                {processedData.overall?.totalDependents || 0}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Additional family members
                            </Typography>
                        </CardContent>
                    </Card>
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

            {/* Individual country sections */}
            {sortedCountries.map(country => (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }} key={country}>
                    <Typography
                        variant="h5"
                        gutterBottom
                        sx={{
                            backgroundColor: CustomColors.UIGrey200, // Filled background
                            color: CustomColors.UIGrey800, // Contrasting font color
                            padding: '8px 16px', // Add padding for better spacing
                            borderRadius: '4px' // Optional: slight rounding for aesthetics
                        }}
                    >
                        {country} Health Insurance Overview
                    </Typography>
                    <Divider sx={{ mb: 2 }} />

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
                                    {(processedData.plansByCountry[country] || [])
                                        .sort((a, b) => b.count - a.count)
                                        .map((plan) => (
                                            <TableRow key={plan.id} hover>
                                                <TableCell>{plan.name}</TableCell>
                                                <TableCell align="right">{plan.count}</TableCell>
                                                <TableCell align="right">
                                                    {plan.count > 0
                                                        ? formatPercentage(plan.percentage)
                                                        : '0.0%'
                                                    }
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    {/* Summary row */}
                                    <TableRow sx={{ backgroundColor: CustomColors.UIGrey100 }}>
                                        <TableCell sx={{ fontWeight: 'bold' }}>Total</TableCell>
                                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                            {processedData.countrySummary[country]?.totalWithInsurance || 0}
                                        </TableCell>
                                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                            {formatPercentage(processedData.countrySummary[country]?.coveragePercentage)}
                                        </TableCell>
                                    </TableRow>
                                </TableBody>
                            </Table>

                            {/* Dependents info for this country */}
                            {processedData.dependentsByCountry[country] && (
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
                                                <TableCell align="right">{processedData.dependentsByCountry[country].count}</TableCell>
                                            </TableRow>
                                            <TableRow hover>
                                                <TableCell>Contracts with Dependents</TableCell>
                                                <TableCell align="right">
                                                    {formatPercentage(processedData.dependentsByCountry[country].percentage)}
                                                </TableCell>
                                            </TableRow>
                                        </TableBody>
                                    </Table>
                                </Box>
                            )}
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Box sx={{ height: 400 }}>
                                <EChartsComponent option={getCountryBarChartOptions(country)} />
                            </Box>
                        </Grid>
                    </Grid>
                </Paper>
            ))}
        </Container>
    );
};

export default HealthInsuranceDashboard;