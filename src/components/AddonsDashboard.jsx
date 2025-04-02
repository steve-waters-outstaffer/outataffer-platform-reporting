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
    CardContent
} from '@mui/material';
import { CustomColors } from '../theme';
import { fetchLatestAddonMetrics } from '../services/ApiService';
import EChartsComponent from './Chart';

const CATEGORY_ORDER = [
    'plan',
    'device',
    'os_choice',
    'hardware_addon',
    'membership_addon',
    'software_addon',
    'country'

];

const AddonsDashboard = () => {
    const [addonData, setAddonData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await fetchLatestAddonMetrics();
                setAddonData(data);
                setLoading(false);
            } catch (err) {
                console.error('Error fetching add-on metrics:', err);
                setError('Failed to load addon metrics');
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const formatPercentage = (value) => `${value.toFixed(1)}%`;

    const getTopItem = (groupedData, category) => {
        const items = groupedData[category];
        if (!items || items.length === 0) return null;
        return [...items].sort((a, b) => b.count - a.count)[0];
    };

    const groupedData = addonData
        ? addonData.reduce((acc, item) => {
            const category = item.metric_type;
            if (!acc[category]) acc[category] = [];
            acc[category].push(item);
            return acc;
        }, {})
        : {};

    const getCountryChartOptions = () => {
        const entries = groupedData['country'];
        if (!entries) return {};

        const sorted = [...entries].sort((a, b) => b.count - a.count).slice(0, 10).reverse();

        return {
            title: {
                text: 'Top Countries by Usage',
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
                    data: sorted.map((item) => item.count),
                    itemStyle: {
                        color: CustomColors.MidnightBlue
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
                    Add-ons Overview
                </Typography>
                <Typography variant="body" color="text.secondary" gutterBottom>
                    Subscriptions with add-on optins for devices, software, and hardware add-ons as of {addonData?.[0]?.snapshot_date || 'latest'}
                </Typography>
            </Paper>

            <Grid container spacing={3} sx={{ mb: 3 }}>
                {[
                    { label: 'PLAN', category: 'plan', color: CustomColors.MidnightBlue, dark: true },
                    { label: 'DEVICE', category: 'device', color: CustomColors.DeepSkyBlue },
                    { label: 'HARDWARE', category: 'hardware_addon', color: CustomColors.Meadow },
                    { label: 'SOFTWARE', category: 'software_addon', color: CustomColors.Purple }
                ].map(({ label, category, color, dark }) => {
                    const topItem = getTopItem(groupedData, category);
                    return (
                        <Grid item xs={12} sm={6} md={3} key={category}>
                            <Card
                                sx={{
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    bgcolor: dark ? color : 'white',
                                    color: dark ? 'white' : 'inherit'
                                }}
                            >
                                <CardContent>
                                    <Typography
                                        variant="h7"
                                        gutterBottom
                                        sx={{ color: dark ? 'white' : 'text.secondary' }}
                                    >
                                        TOP {label}
                                    </Typography>
                                    <Typography
                                        variant="h3"
                                        component="div"
                                        sx={{ mt: 2, mb: 1, color: dark ? 'white' : color }}
                                    >
                                        {topItem ? topItem.count : '—'}
                                    </Typography>
                                    <Typography
                                        variant="bodySmall"
                                        sx={{ color: dark ? 'white' : 'text.secondary' }}
                                    >
                                        {topItem ? topItem.label : 'N/A'}
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>
                    );
                })}
            </Grid>

            {/* Country Breakdown Chart */}
            {groupedData['country'] && (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                    <Typography variant="h5" gutterBottom>Country Overview</Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Box sx={{ height: 400 }}>
                        <EChartsComponent option={getCountryChartOptions()} />
                    </Box>
                </Paper>
            )}

            {CATEGORY_ORDER.map((category) => {
                if (category === 'country') return null;
                const entries = groupedData[category];
                if (!entries) return null;

                return (
                    <Paper elevation={1} sx={{ p: 3, mb: 3 }} key={category}>
                        <Typography variant="h5" gutterBottom sx={{ textTransform: 'capitalize' }}>
                            {category.replace('_', ' ')}
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Table>
                            <TableHead>
                                <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                    <TableCell sx={{ fontWeight: 'bold', width: '40%' }}>Label</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>Count</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>% of Subscriptions</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold', width: '20%' }}>% of Category</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {[...entries]
                                    .sort((a, b) => b.count - a.count)
                                    .map((item) => (
                                        <TableRow key={item.id}>
                                            <TableCell sx={{ width: '40%' }}>{item.label}</TableCell>
                                            <TableCell align="right" sx={{ width: '20%' }}>{item.count}</TableCell>
                                            <TableCell align="right" sx={{ width: '20%' }}>{formatPercentage(Number(item.overall_percentage))}</TableCell>
                                            <TableCell align="right" sx={{ width: '20%' }}>{formatPercentage(Number(item.category_percentage))}</TableCell>
                                        </TableRow>
                                    ))}
                                {/* Totals Row */}
                                <TableRow sx={{ backgroundColor: CustomColors.UIGrey100 }}>
                                    <TableCell sx={{ fontWeight: 'bold' }}>Total</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                        {entries.reduce((sum, item) => sum + Number(item.count), 0)}
                                    </TableCell>


                                    <TableCell colSpan={2} />
                                </TableRow>
                            </TableBody>
                        </Table>
                    </Paper>
                );
            })}
        </Container>
    );
};

export default AddonsDashboard;
