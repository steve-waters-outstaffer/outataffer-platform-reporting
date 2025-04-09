// src/components/GeographicDashboard.jsx
import React, { useState, useEffect } from 'react';
import CountryFlag from './common/CountryFlag';
import {
    Box,
    Grid,
    Paper,
    Typography,
    AppBar,
    Divider,
    Card,
    CardContent,
    CircularProgress,
    Container,
    Button,
    Table,
    TableHead,
    TableBody,
    TableRow,
    Toolbar,
    TableCell,
    Alert
} from '@mui/material';
import EChartsComponent from './Chart';
import { CustomColors } from '../theme';
import { useNavigate } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useAuth } from '../contexts/AuthContext';
import { logoutUser } from '../services/AuthService.js';
// At the top of GeographicDashboard.jsx - Add this import
import { fetchGeographicMetrics } from '../services/ApiService';

// Add this function to your ApiService.js file
// export const fetchGeographicMetrics = async () => {
//     try {
//         const timestamp = new Date().getTime();
//         return apiRequest(`/geography/countries?_=${timestamp}`);
//     } catch (error) {
//         console.warn("Geographic metrics API error, using fallback data:", error);
//         return { snapshot_date: "2025-04-09", countries: [], totals: {} };
//     }
// };

const GeographicDashboard = () => {
    const navigate = useNavigate();
    const [countryData, setCountryData] = useState(null);
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
                const data = await fetchGeographicMetrics();
                setCountryData(data);
                setLoading(false);
            } catch (err) {
                console.error("Error fetching geographic data:", err);
                setError("Failed to load geographic data. Please try again later.");
                setLoading(false);
            }
        };

        fetchData();
    }, []);

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

    // Chart options for country breakdown
    const getCountryChartOptions = () => {
        if (!countryData || !countryData.countries || countryData.countries.length === 0) return {};

        // Get all countries for the chart, sorted by active contracts
        const chartData = [...countryData.countries]
            .filter(country => country.metrics.active_contracts?.count > 0)
            .sort((a, b) =>
                (b.metrics.active_contracts?.count || 0) - (a.metrics.active_contracts?.count || 0)
            );

        return {
            title: {
                text: 'Active Contracts by Country',
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
                    const country = chartData[data.dataIndex];
                    return `${country.name}: ${country.metrics.active_contracts.count} contracts (${formatPercentage(country.metrics.active_contracts.percentage)})`;
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
                    formatter: (value) => value
                }
            },
            yAxis: {
                type: 'category',
                data: chartData.map(item => item.name),
                inverse: true,
                axisLabel: {
                    color: CustomColors.UIGrey700
                }
            },
            series: [
                {
                    name: 'Active Contracts',
                    type: 'bar',
                    data: chartData.map(item => item.metrics.active_contracts.count),
                    itemStyle: {
                        color: CustomColors.DeepSkyBlue
                    },
                    label: {
                        show: true,
                        position: 'right',
                        formatter: (params) => params.value
                    }
                }
            ]
        };
    };

    // Chart options for revenue breakdown
    const getRevenueChartOptions = () => {
        if (!countryData || !countryData.countries || countryData.countries.length === 0) return {};

        // Get all countries for the chart, sorted by MRR
        const chartData = [...countryData.countries]
            .filter(country => country.metrics.mrr?.value_aud > 0)
            .sort((a, b) =>
                (b.metrics.mrr?.value_aud || 0) - (a.metrics.mrr?.value_aud || 0)
            );

        return {
            title: {
                text: 'Monthly Recurring Revenue by Country',
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
                    const country = chartData[data.dataIndex];
                    return `${country.name}: ${formatCurrency(country.metrics.mrr.value_aud)} (${formatPercentage(country.metrics.mrr.percentage)})`;
                }
            },
            grid: {
                left: '3%',
                right: '10%',
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
                data: chartData.map(item => item.name),
                inverse: true,
                axisLabel: {
                    color: CustomColors.UIGrey700
                }
            },
            series: [
                {
                    name: 'MRR',
                    type: 'bar',
                    data: chartData.map(item => item.metrics.mrr.value_aud),
                    itemStyle: {
                        color: CustomColors.MidnightBlue
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
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <CircularProgress color="secondary" />
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <Alert severity="error" sx={{ width: '100%', maxWidth: 600 }}>{error}</Alert>
            </Box>
        );
    }

    // Sort countries for display - active ones first, then alphabetically
    const sortedCountries = countryData.countries
        .sort((a, b) => {
            // First by active contracts (descending)
            const aActive = a.metrics.active_contracts?.count || 0;
            const bActive = b.metrics.active_contracts?.count || 0;
            if (bActive !== aActive) {
                return bActive - aActive;
            }
            // Then alphabetically
            return a.name.localeCompare(b.name);
        });

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
        </AppBar>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Paper elevation={1} sx={{ p: 3, mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom>
                        Geographic Distribution Dashboard
                    </Typography>
                    <Typography variant="body" color="text.secondary" gutterBottom>
                        Geographical distribution of contracts and revenue as of {new Date(countryData.snapshot_date).toLocaleDateString('en-AU', { year: 'numeric', month: 'long', day: 'numeric' })}
                    </Typography>
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

            {/* Summary metrics */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: CustomColors.MidnightBlue, color: 'white' }}>
                        <CardContent>
                            <Typography variant="h7" gutterBottom>
                                ACTIVE CONTRACTS
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>
                                {countryData.totals.active_contracts}
                            </Typography>
                            <Typography variant="bodySmall">
                                Across {sortedCountries.filter(c => c.metrics.active_contracts?.count > 0).length} countries
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                MONTHLY REVENUE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.DeepSkyBlue }}>
                                {formatCurrency(countryData.totals.mrr)}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                MRR across all countries
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                ANNUAL REVENUE
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Meadow }}>
                                {formatCurrency(countryData.totals.arr)}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                ARR across all countries
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent>
                            <Typography variant="h7" color="text.secondary" gutterBottom>
                                COUNTRIES WITH CONTRACTS
                            </Typography>
                            <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Purple }}>
                                {sortedCountries.filter(c => c.metrics.active_contracts?.count > 0).length}
                            </Typography>
                            <Typography variant="bodySmall" color="text.secondary">
                                Out of {sortedCountries.length} available countries
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Detailed country cards */}
            <Typography variant="h5" sx={{ mb: 2, mt: 4 }}>Country Details</Typography>
            <Grid container spacing={3} sx={{ mb:3 }}>
                {sortedCountries.map((country) => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={country.id}>
                        <Card sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            borderLeft: `4px solid ${(country.metrics.active_contracts?.count > 0 || country.metrics.offboarding_contracts?.count > 0) ? CustomColors.DeepSkyBlue : CustomColors.UIGrey300}`,
                            opacity: (country.metrics.active_contracts?.count > 0 || country.metrics.offboarding_contracts?.count > 0) ? 1 : 0.8
                        }}>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h6" component="div" gutterBottom>
                                        {country.name}
                                    </Typography>
                                    <Typography variant="h3" sx={{ fontSize: '2rem' }}>
                                        <CountryFlag countryCode={country.id} size={32} />
                                    </Typography>
                                </Box>

                                <Grid container spacing={1}>
                                    <Grid item xs={6}>
                                        <Typography variant="bodySmall" color="text.secondary">Active:</Typography>
                                        <Typography variant="h6">{(country.metrics.active_contracts?.count || 0)-(country.metrics.offboarding_contracts?.count || 0)}</Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="bodySmall" color="text.secondary">Offboarding:</Typography>
                                        <Typography variant="h6">{country.metrics.offboarding_contracts?.count || 0}</Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="bodySmall" color="text.secondary">Not Started:</Typography>
                                        <Typography variant="h6">{country.metrics.approved_not_started?.count || 0}</Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="bodySmall" color="text.secondary">Total:</Typography>
                                        <Typography variant="h6">
                                            {(country.metrics.active_contracts?.count || 0) +
                                                (country.metrics.approved_not_started?.count || 0)}
                                        </Typography>
                                    </Grid>
                                </Grid>

                                <Divider sx={{ my: 1.5 }} />

                                <Grid container spacing={1}>
                                    <Grid item xs={6}>
                                        <Typography variant="bodySmall" color="text.secondary">MRR:</Typography>
                                        <Typography variant="h6" sx={{ color: CustomColors.MidnightBlue }}>
                                            {formatCurrency(country.metrics.mrr?.value_aud || 0)}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="bodySmall" color="text.secondary">ARR:</Typography>
                                        <Typography variant="h6" sx={{ color: CustomColors.DeepSkyBlue }}>
                                            {formatCurrency(country.metrics.arr?.value_aud || 0)}
                                        </Typography>
                                    </Grid>
                                </Grid>

                                {(country.metrics.mrr?.percentage > 0) && (
                                    <Typography variant="bodySmall" color="text.secondary" sx={{ mt: 1 }}>
                                        {formatPercentage(country.metrics.mrr?.percentage)} of total MRR
                                    </Typography>
                                )}
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* Charts */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2 }}>
                        <Box sx={{ height: 400 }}>
                            <EChartsComponent option={getCountryChartOptions()} />
                        </Box>
                    </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Paper elevation={1} sx={{ p: 2 }}>
                        <Box sx={{ height: 400 }}>
                            <EChartsComponent option={getRevenueChartOptions()} />
                        </Box>
                    </Paper>
                </Grid>
            </Grid>

            {/* Country summary table */}
            <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h5" gutterBottom>Supported EOR employee countries</Typography>
                <Divider sx={{ mb: 2 }} />
                <Table>
                    <TableHead>
                        <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                            <TableCell sx={{ fontWeight: 'bold' }}>Country</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Active EOR</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Offboarding soon</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Approved Not Started</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>MRR</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>ARR</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {sortedCountries.map((country) => (
                            <TableRow key={country.id} hover>
                                <TableCell>
                                    <Box sx={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 2  // Add gap between items (8px × 2 = 16px)
                                    }}>
                                        <Typography sx={{ fontSize: '1.5rem', lineHeight: 1 }}>
                                            <CountryFlag countryCode={country.id} size={20} variant="code" />
                                        </Typography>
                                        {country.name}
                                    </Box>
                                </TableCell>
                                <TableCell align="right">
                                    {(country.metrics.active_contracts?.count || 0)- (country.metrics.offboarding_contracts?.count || 0) }
                                </TableCell>
                                <TableCell align="right">
                                    {country.metrics.offboarding_contracts?.count || 0}
                                </TableCell>
                                <TableCell align="right">
                                    {country.metrics.approved_not_started?.count || 0}
                                </TableCell>
                                <TableCell align="right">
                                    {formatCurrency(country.metrics.mrr?.value_aud || 0)}
                                </TableCell>
                                <TableCell align="right">
                                    {formatCurrency(country.metrics.arr?.value_aud || 0)}
                                </TableCell>

                            </TableRow>
                        ))}
                        <TableRow sx={{ backgroundColor: CustomColors.UIGrey100, fontWeight: 'bold' }}>
                            <TableCell sx={{ fontWeight: 'bold' }}>Total</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{(countryData.totals.active_contracts) - (countryData.totals.offboarding_contracts)}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{countryData.totals.offboarding_contracts}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{countryData.totals.approved_not_started}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{formatCurrency(countryData.totals.mrr)}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>{formatCurrency(countryData.totals.arr)}</TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </Paper>
        </Container>
        </Box>
    );
};

export default GeographicDashboard;