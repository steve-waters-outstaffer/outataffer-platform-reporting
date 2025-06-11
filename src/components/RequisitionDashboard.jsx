// src/components/RequisitionDashboard.jsx
import React, { useState, useEffect } from 'react';
import BetaWatermark from './BetaWatermark';
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
import { fetchLatestRequisitionMetrics, fetchRequisitionTrend } from '../services/ApiService';

const RequisitionDashboard = () => {
    const navigate = useNavigate();
    const [metricData, setMetricData] = useState(null);
    const [trendData, setTrendData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { currentUser } = useAuth();

    const handleLogout = async () => {
        try {
            await logoutUser();
            navigate('/login');
        } catch (err) {
            console.error('Logout error:', err);
        }
    };

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);
                const [latest, trend] = await Promise.all([
                    fetchLatestRequisitionMetrics(),
                    fetchRequisitionTrend(6)
                ]);
                setMetricData(latest);
                setTrendData(trend);
                setLoading(false);
            } catch (err) {
                console.error('Error fetching requisition data:', err);
                setError('Failed to load requisition data. Please try again later.');
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const formatCurrency = (value) => {
        if (value === null || value === undefined) return '-';
        return new Intl.NumberFormat('en-AU', {
            style: 'currency',
            currency: 'AUD',
            maximumFractionDigits: 0
        }).format(value);
    };

    const getTrendOptions = () => {
        const months = trendData.map(t => t.month);
        const values = trendData.map(t => t.positions);
        return {
            tooltip: { trigger: 'axis' },
            grid: { left: '10%', right: '15%', bottom: '15%', top: '10%', containLabel: true },
            xAxis: { type: 'category', boundaryGap: false, data: months, axisLabel: { color: CustomColors.UIGrey700, margin: 14 } },
            yAxis: { type: 'value' },
            series: [{
                name: 'Approved Positions',
                type: 'line',
                data: values,
                symbol: 'circle',
                lineStyle: { color: CustomColors.UIGrey400, width: 2 },
                itemStyle: { color: CustomColors.DeepSkyBlue }
            }]
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

    const { countries = [], totals = {}, snapshot_month } = metricData || {};

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
                    <Typography variant="h4" color="text.secondary" align={'center'}>
                        This dashboard is in beta and may display incomplete information, some data may be missing or out of date. Please do not rely on this dashboard for critical decisions or reporting purposes.
                    </Typography>
                </Box>
            </AppBar>
            <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <BetaWatermark />
                <Paper elevation={1} sx={{ p: 3, mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                        <Typography variant="h4" component="h1" gutterBottom>
                            Requisitions Dashboard
                        </Typography>
                        <Typography variant="body" color="text.secondary" gutterBottom>
                            Metrics for {snapshot_month}
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

                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: CustomColors.MidnightBlue, color: 'white' }}>
                            <CardContent>
                                <Typography variant="h7" gutterBottom>
                                    APPROVED REQUISITIONS
                                </Typography>
                                <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1 }}>
                                    {totals.approved_requisitions}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                            <CardContent>
                                <Typography variant="h7" color="text.secondary" gutterBottom>
                                    OPEN POSITIONS
                                </Typography>
                                <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.DeepSkyBlue }}>
                                    {totals.open_positions}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                            <CardContent>
                                <Typography variant="h7" color="text.secondary" gutterBottom>
                                    PROJECTED MRR
                                </Typography>
                                <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Meadow }}>
                                    {formatCurrency(totals.mrr)}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                            <CardContent>
                                <Typography variant="h7" color="text.secondary" gutterBottom>
                                    PROJECTED ARR
                                </Typography>
                                <Typography variant="h3" component="div" sx={{ mt: 2, mb: 1, color: CustomColors.Purple }}>
                                    {formatCurrency(totals.arr)}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>

                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={6}>
                        <Paper elevation={1} sx={{ p: 2 }}>
                            <Typography variant="h6" gutterBottom>Positions Approved Per Month</Typography>
                            <Box sx={{ height: 380 }}><EChartsComponent option={getTrendOptions()} /></Box>
                        </Paper>
                    </Grid>
                </Grid>

                <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                    <Typography variant="h5" gutterBottom>Country Summary</Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Table>
                        <TableHead>
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                <TableCell sx={{ fontWeight: 'bold' }}>Country</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Approved Req.</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Approved Positions</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Open Positions</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Projected MRR</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {countries.map((c) => (
                                <TableRow key={c.id} hover>
                                    <TableCell>{c.name}</TableCell>
                                    <TableCell align="right">{c.metrics.approved_requisitions.count}</TableCell>
                                    <TableCell align="right">{c.metrics.approved_positions.count}</TableCell>
                                    <TableCell align="right">{c.metrics.open_positions.count}</TableCell>
                                    <TableCell align="right">{formatCurrency(c.metrics.mrr.value_aud)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </Paper>
            </Container>
        </Box>
    );
};

export default RequisitionDashboard;
