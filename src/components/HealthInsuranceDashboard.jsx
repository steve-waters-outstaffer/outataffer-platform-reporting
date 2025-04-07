import React, { useState, useEffect, useMemo } from 'react';
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
import { fetchLatestHealthInsuranceMetrics } from '../services/ApiService';
import { useNavigate } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

const HealthInsuranceDashboard = () => {
    const navigate = useNavigate();
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [processedData, setProcessedData] = useState({
        snapshot_date: null,
        plansByCountry: {},
        countrySummary: {},
        overall: {},
        dependentsByCountry: {},
        allPlans: [],
        crossCountryPlans: []
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);
                const timestamp = new Date().getTime();
                const data = await fetchLatestHealthInsuranceMetrics(`?_=${timestamp}`);
                setHealthData(data);
                const processed = processHealthData(data);
                setProcessedData(processed);
                setLoading(false);
            } catch (err) {
                setError("Failed to load health insurance data. Please try again later.");
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const processHealthData = (data) => {
        if (!data || !Array.isArray(data) || data.length === 0) {
            return {
                snapshot_date: null,
                plansByCountry: {},
                countrySummary: {},
                overall: {},
                dependentsByCountry: {},
                allPlans: [],
                crossCountryPlans: []
            };
        }

        const result = {
            snapshot_date: data[0]?.snapshot_date,
            plansByCountry: {},
            countrySummary: {},
            overall: {},
            dependentsByCountry: {},
            allPlans: [],
            crossCountryPlans: []
        };

        const uniquePlans = new Set();
        data.forEach(item => {
            if (item.metric_type === 'health_insurance_plan_by_country') {
                uniquePlans.add(item.id);
            }
        });

        result.allPlans = Array.from(uniquePlans).map(planId => {
            const matchingItem = data.find(item => item.metric_type === 'health_insurance_plan_by_country' && item.id === planId);
            const planCountryMatch = matchingItem?.label.match(/^(.*?)(?:\s*\(.*?\))?$/);
            return { id: planId, name: planCountryMatch ? planCountryMatch[1] : matchingItem?.label || planId };
        });

        data.forEach(item => {
            if (item.metric_type === 'health_insurance_plan_by_country') {
                const planCountryMatch = item.label.match(/\((.*?)\)$/);
                const planCountry = planCountryMatch ? planCountryMatch[1] : 'Unknown';
                const planName = item.label.replace(` (${planCountry})`, '');
                result.plansByCountry[planCountry] = result.plansByCountry[planCountry] || [];
                result.plansByCountry[planCountry].push({
                    id: item.id,
                    name: planName,
                    count: parseInt(item.count),
                    percentage: parseFloat(item.overall_percentage),
                    isMultiCountry: item.is_multi_country || false
                });
            } else if (item.metric_type === 'health_insurance_total_by_country') {
                result.countrySummary[item.id] = result.countrySummary[item.id] || {};
                result.countrySummary[item.id].totalWithInsurance = parseInt(item.count);
                result.countrySummary[item.id].coveragePercentage = parseFloat(item.overall_percentage);
            } else if (item.metric_type === 'eligible_contracts_by_country') {
                result.countrySummary[item.id] = result.countrySummary[item.id] || {};
                result.countrySummary[item.id].totalEligible = parseInt(item.count);
            } else if (item.metric_type === 'health_insurance_dependents_by_country') {
                result.dependentsByCountry[item.id] = {
                    count: parseInt(item.count),
                    percentage: parseFloat(item.overall_percentage),
                    contractCount: parseInt(item.contract_count)
                };
            }
        });

        const crossCountryPlans = {};
        Object.entries(result.plansByCountry).forEach(([country, plans]) => {
            plans.forEach(plan => {
                if (!crossCountryPlans[plan.id]) {
                    crossCountryPlans[plan.id] = {
                        id: plan.id,
                        name: plan.name,
                        countries: {},
                        totalCount: 0,
                        isMultiCountry: plan.isMultiCountry
                    };
                }
                crossCountryPlans[plan.id].countries[country] = {
                    count: plan.count,
                    percentage: plan.percentage
                };
                crossCountryPlans[plan.id].totalCount += plan.count;
            });
        });

        result.crossCountryPlans = Object.values(crossCountryPlans)
            .filter(plan => plan.isMultiCountry || Object.keys(plan.countries).length > 1)
            .sort((a, b) => b.totalCount - a.totalCount);

        // Calculate overall metrics
        const totalWithInsurance = Object.values(result.countrySummary).reduce((sum, country) => sum + (country.totalWithInsurance || 0), 0);
        const totalEligible = Object.values(result.countrySummary).reduce((sum, country) => sum + (country.totalEligible || 0), 0);
        const totalDependents = Object.values(result.dependentsByCountry).reduce((sum, country) => sum + (country.count || 0), 0);
        const overallCoveragePercentage = totalEligible > 0 ? (totalWithInsurance / totalEligible) * 100 : 0;

        // Find top coverage country
        let topCoverageCountry = 'N/A';
        let topCoveragePercentage = 0;
        Object.entries(result.countrySummary).forEach(([country, summary]) => {
            if (summary.coveragePercentage > topCoveragePercentage) {
                topCoveragePercentage = summary.coveragePercentage;
                topCoverageCountry = country;
            }
        });

        result.overall = {
            totalWithInsurance,
            totalEligible,
            totalDependents,
            overallCoveragePercentage,
            topCoverageCountry,
            topCoveragePercentage
        };

        // New: Calculate total plan usage across all countries
        const planUptakeSummary = result.allPlans.map(plan => {
            let total = 0;
            const countries = [];

            Object.entries(result.plansByCountry).forEach(([country, plans]) => {
                const match = plans.find(p => p.id === plan.id);
                if (match) {
                    total += match.count;
                    countries.push(country);
                }
            });

            return {
                id: plan.id,
                name: plan.name,
                totalEmployees: total,
                uptakePercentage: (total / result.overall.totalEligible * 100) || 0,
                countries
            };
        });

        result.planUptakeSummary = planUptakeSummary;

        return result;
    };

    const formatPercentage = (value) => value === undefined || value === null ? '0.0%' : `${value.toFixed(1)}%`;

    const getCrossCountryPlanChartOptions = useMemo(() => {
        if (!processedData?.crossCountryPlans || processedData.crossCountryPlans.length === 0) return {};
        const topPlans = processedData.crossCountryPlans.slice(0, 5);

        return {
            title: {
                text: 'Cross-Country Insurance Plans',
                left: 'center',
                textStyle: { color: CustomColors.UIGrey800 }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: (params) => {
                    const item = params[0];
                    return `${item.name}: ${item.value} employees`;
                }
            },
            grid: { left: '20%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { type: 'value' },
            yAxis: {
                type: 'category',
                data: topPlans.map(plan => plan.name),
                axisLabel: { color: CustomColors.UIGrey700 },
                inverse: true
            },
            series: [{
                name: 'Employees',
                type: 'bar',
                data: topPlans.map(plan => ({
                    value: plan.totalCount,
                    itemStyle: {
                        color: plan.totalCount > 0 ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300
                    }
                })),
                label: {
                    show: true,
                    position: 'right',
                    formatter: '{c}'
                }
            }]
        };
    }, [processedData.crossCountryPlans]);

   const getCountryBarChartOptions = (country) => {
        const plans = (processedData.plansByCountry[country] || []).sort((a, b) => b.count - a.count);
        return {
            title: { text: `${country} Health Insurance Plan Distribution`, left: 'center', top: '5%', textStyle: { color: CustomColors.UIGrey800, fontSize: 15, fontWeight: 'normal' } },
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (params) => `${params[0].name}: ${params[0].value} (${params[0].value > 0 ? formatPercentage(params[0].value / processedData.countrySummary[country]?.totalWithInsurance * 100) : '0.0%'})` },
            grid: { left: '20%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { type: 'value' },
            yAxis: { type: 'category', data: plans.map(plan => plan.name), axisLabel: { color: CustomColors.UIGrey700, fontSize: 11 }, inverse: true },
            series: [{
                name: 'Employees',
                type: 'bar',
                data: plans.map(plan => ({ value: plan.count, itemStyle: { color: plan.count > 0 ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300 } })),
                label: { show: true, position: 'right', formatter: '{c}' }
            }]
        };
    };

    const getCountriesComparisonChartOptions = useMemo(() => {
        const summaryData = processedData.countrySummary || {};
        const countries = Object.keys(summaryData).sort((a, b) => (summaryData[b]?.totalWithInsurance || 0) - (summaryData[a]?.totalWithInsurance || 0));
        return {
            title: { text: 'Insurance Coverage by Country', left: 'center', textStyle: { color: CustomColors.UIGrey800 } },
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (params) => `${params[0].name}: ${params[0].value} of ${summaryData[params[0].name]?.totalEligible || 0} employees (${formatPercentage(params[0].value2)})` },
            grid: { left: '20%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { type: 'value' },
            yAxis: { type: 'category', data: countries, axisLabel: { color: CustomColors.UIGrey700 }, inverse: true },
            series: [{
                name: 'Employees with Coverage',
                type: 'bar',
                data: countries.map(country => ({
                    value: summaryData[country].totalWithInsurance,
                    value2: summaryData[country].coveragePercentage,
                    itemStyle: { color: summaryData[country].coveragePercentage >= 99 ? CustomColors.SecretGarden : CustomColors.DeepSkyBlue }
                })),
                label: { show: true, position: 'right', formatter: (params) => `${params.value} (${formatPercentage(summaryData[params.name].coveragePercentage)})` }
            }]
        };
    }, [processedData.countrySummary]);

    const sortedCountries = Object.keys(processedData.countrySummary || {}).sort((a, b) => (processedData.countrySummary[b]?.totalWithInsurance || 0) - (processedData.countrySummary[a]?.totalWithInsurance || 0));

    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Paper elevation={1} sx={{ p: 3, mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom>Health Insurance Dashboard</Typography>
                    <Typography variant="body" color="text.secondary" gutterBottom>
                        Health insurance metrics as of {new Date(processedData.snapshot_date).toLocaleDateString('en-AU', { year: 'numeric', month: 'long', day: 'numeric' })}
                    </Typography>
                </Box>
                <Button startIcon={<ArrowBackIcon fontSize="small" />} onClick={() => navigate('/dashboard')} sx={{ fontSize: '0.725rem', px: 1, py: 0.25, minWidth: 'unset', borderRadius: '20px', border: '1px solid', borderColor: CustomColors.DeepSkyBlue, color: CustomColors.DeepSkyBlue, '&:hover': { backgroundColor: `${CustomColors.DeepSkyBlue}10` } }}>
                    Main Dashboard
                </Button>
            </Paper>

            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: CustomColors.MidnightBlue, color: 'white' }}>
                        <CardContent>
                            <Typography variant="h7" gutterBottom>OVERALL COVERAGE RATE</Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>{formatPercentage(processedData.overall?.overallCoveragePercentage)}</Typography>
                            <Typography variant="bodySmall">{processedData.overall?.totalWithInsurance} of {processedData.overall?.totalEligible} eligible contracts</Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>TOTAL COVERED EMPLOYEES</Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.DeepSkyBlue }}>{processedData.overall?.totalWithInsurance || 0}</Typography>
                            <Typography variant="bodySmall" color="text.secondary">Total employees with insurance</Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>TOP COVERAGE COUNTRY</Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Meadow }}>{processedData.overall?.topCoverageCountry || 'N/A'}</Typography>
                            <Typography variant="bodySmall" color="text.secondary">{formatPercentage(processedData.overall?.topCoveragePercentage)} coverage rate</Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>DEPENDENTS COVERED</Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Purple }}>{processedData.overall?.totalDependents || 0}</Typography>
                            <Typography variant="bodySmall" color="text.secondary">Additional family members</Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h5" gutterBottom>Country Comparison</Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ height: 400 }}><EChartsComponent option={getCountriesComparisonChartOptions} /></Box>
            </Paper>

            {/*Summary table */}
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h5" gutterBottom>
                    Health Insurance Plan Usage (All Countries)
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Table>
                    <TableHead>
                        <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                            <TableCell sx={{ fontWeight: 'bold' }}>Plan</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Employees</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Uptake %</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Countries</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {processedData.planUptakeSummary
                            .sort((a, b) => b.totalEmployees - a.totalEmployees)
                            .map(plan => (
                                <TableRow key={plan.id}>
                                    <TableCell>{plan.name}</TableCell>
                                    <TableCell align="right">{plan.totalEmployees}</TableCell>
                                    <TableCell align="right">{formatPercentage(plan.uptakePercentage)}</TableCell>
                                    <TableCell>{plan.countries.join(', ')}</TableCell>
                                </TableRow>
                            ))}
                    </TableBody>
                </Table>
            </Paper>

            {/* Update country table render to filter by available plans*/}
            {sortedCountries.map(country => (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }} key={country}>
                    <Typography variant="h5" gutterBottom sx={{ backgroundColor: CustomColors.UIGrey200, color: CustomColors.UIGrey800, padding: '8px 16px', borderRadius: '4px' }}>
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
                                        .filter(plan => processedData.allPlans.some(p => p.id === plan.id))
                                        .sort((a, b) => b.count - a.count)
                                        .map(plan => (
                                            <TableRow key={plan.id} hover>
                                                <TableCell>{plan.name}</TableCell>
                                                <TableCell align="right">{plan.count}</TableCell>
                                                <TableCell align="right">{plan.count > 0 ? formatPercentage(plan.percentage) : '0.0%'}</TableCell>
                                            </TableRow>
                                        ))}
                                    <TableRow sx={{ backgroundColor: CustomColors.UIGrey100 }}>
                                        <TableCell sx={{ fontWeight: 'bold' }}>Total</TableCell>
                                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>{processedData.countrySummary[country]?.totalWithInsurance || 0}</TableCell>
                                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>{formatPercentage(processedData.countrySummary[country]?.coveragePercentage)}</TableCell>
                                    </TableRow>
                                </TableBody>
                            </Table>

                            {/* Add Dependents Table */}
                            {processedData.dependentsByCountry[country] && (
                                <>
                                    <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>Dependents Covered</Typography>
                                    <Table>
                                        <TableHead>
                                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                                <TableCell sx={{ fontWeight: 'bold' }}>Dependents</TableCell>
                                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Count</TableCell>
                                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Percentage</TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            <TableRow hover>
                                                <TableCell>Dependents</TableCell>
                                                <TableCell align="right">{processedData.dependentsByCountry[country].count}</TableCell>
                                                <TableCell align="right">{formatPercentage(processedData.dependentsByCountry[country].percentage)}</TableCell>
                                            </TableRow>
                                        </TableBody>
                                    </Table>
                                </>
                            )}
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Box sx={{ height: 400 }}><EChartsComponent option={getCountryBarChartOptions(country)} /></Box>
                        </Grid>
                    </Grid>
                </Paper>
            ))}

            <Paper elevation={1} sx={{ p: 3, mb: 3 }} key="cross-country">
                <Typography variant="h5" gutterBottom sx={{ backgroundColor: CustomColors.UIGrey200, color: CustomColors.UIGrey800, padding: '8px 16px', borderRadius: '4px' }}>
                    Insurance Plans Across Multiple Countries
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {processedData.crossCountryPlans?.length > 0 ? (
                    <Table>
                        <TableHead>
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                <TableCell sx={{ fontWeight: 'bold' }}>Insurance Plan</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Total Employees</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Countries</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Distribution</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {processedData.crossCountryPlans.map(plan => (
                                <TableRow key={plan.id} hover>
                                    <TableCell>{plan.name}</TableCell>
                                    <TableCell align="right">{plan.totalCount}</TableCell>
                                    <TableCell>{Object.keys(plan.countries).join(', ')}</TableCell>
                                    <TableCell align="right">
                                        {Object.entries(plan.countries).map(([country, data]) => (
                                            <div key={country}>{country}: {data.count} ({formatPercentage(data.count / plan.totalCount * 100)})</div>
                                        ))}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                ) : (
                    <Typography variant="body1" color="text.secondary">No insurance plans are used across multiple countries.</Typography>
                )}
                {processedData.crossCountryPlans?.length > 0 && (
                    <Box sx={{ height: 370, mt: 3 }}><EChartsComponent option={getCrossCountryPlanChartOptions} /></Box>
                )}
            </Paper>
        </Container>
    );
};

export default HealthInsuranceDashboard;