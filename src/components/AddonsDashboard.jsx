// src/components/AddonsDashboard.jsx
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
    Divider
} from '@mui/material';
import { CustomColors } from '../theme';

// 🔧 Hardcoded snapshot data (simulate BQ result)
const hardcodedAddonData = [
    {
        snapshot_date: '2025-03-31',
        metric_type: 'device',
        id: 'APPLE_AIR_13',
        label: 'Apple MacBook Air 13 (Everyday)',
        count: 5,
        overall_percentage: 3.96,
        category_percentage: 5.26,
        contract_count: 5
    },
    {
        snapshot_date: '2025-03-31',
        metric_type: 'software_addon',
        id: 'INSIGHTFUL',
        label: 'Insightful',
        count: 90,
        overall_percentage: 71.43,
        category_percentage: 98.90,
        contract_count: 90
    },
    {
        snapshot_date: '2025-03-31',
        metric_type: 'hardware_addon',
        id: 'MONITOR_24',
        label: '24” Monitor',
        count: 38,
        overall_percentage: 30.16,
        category_percentage: 84.44,
        contract_count: 38
    }
];

const AddonsDashboard = () => {
    const [addonData, setAddonData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Simulate data fetch with hardcoded values
        try {
            setAddonData(hardcodedAddonData);
            setLoading(false);
        } catch (err) {
            setError('Failed to load addon metrics');
            setLoading(false);
        }
    }, []);

    const formatPercentage = (value) => `${value.toFixed(1)}%`;

    const groupedData = addonData
        ? addonData.reduce((acc, item) => {
            const category = item.metric_type;
            if (!acc[category]) acc[category] = [];
            acc[category].push(item);
            return acc;
        }, {})
        : {};

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
                    Usage of devices, software, and hardware add-ons as of 31 March 2025
                </Typography>
            </Paper>

            {Object.entries(groupedData).map(([category, entries]) => (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }} key={category}>
                    <Typography variant="h5" gutterBottom sx={{ textTransform: 'capitalize' }}>
                        {category.replace('_', ' ')}
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Label</TableCell>
                                <TableCell align="right">Count</TableCell>
                                <TableCell align="right">% of All Contracts</TableCell>
                                <TableCell align="right">% within Category</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {entries.map((item) => (
                                <TableRow key={item.id}>
                                    <TableCell>{item.label}</TableCell>
                                    <TableCell align="right">{item.count}</TableCell>
                                    <TableCell align="right">{formatPercentage(Number(item.overall_percentage))}</TableCell>
                                    <TableCell align="right">{formatPercentage(Number(item.category_percentage))}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </Paper>
            ))}
        </Container>
    );
};

export default AddonsDashboard;