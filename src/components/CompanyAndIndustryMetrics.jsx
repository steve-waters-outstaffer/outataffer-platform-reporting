// src/components/CompanyAndIndustryMetrics.jsx
import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Divider,
    Table,
    TableHead,
    TableBody,
    TableRow,
    TableCell,
    CircularProgress
} from '@mui/material';
import { CustomColors } from '../theme';
import { fetchCompanySizeMetrics, fetchIndustriesByCount, fetchIndustriesByArr } from '../services/ApiService';

const CompanyAndIndustryMetrics = () => {
    const [companySizeData, setCompanySizeData] = useState([]);
    const [industriesByCount, setIndustriesByCount] = useState([]);
    const [industriesByArr, setIndustriesByArr] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                // Fetch all data in parallel
                const [sizeData, countData, arrData] = await Promise.all([
                    fetchCompanySizeMetrics(),
                    fetchIndustriesByCount(5),  // Limit to top 5
                    fetchIndustriesByArr(5)     // Limit to top 5
                ]);

                // Process company size data
                const sizeDistribution = sizeData.filter(item => item.metric_type === 'company_size_distribution');
                const sizeArr = sizeData.filter(item => item.metric_type === 'company_size_arr');
                const sizeAvgArr = sizeData.filter(item => item.metric_type === 'company_size_avg_arr');

                // Combine the three types into one array of size objects
                const combinedSizeData = sizeDistribution.map(item => {
                    const arrItem = sizeArr.find(arr => arr.rank === item.rank);
                    const avgItem = sizeAvgArr.find(avg => avg.rank === item.rank);

                    return {
                        size: item.label,
                        count: item.count,
                        arr: arrItem?.value_aud || 0,
                        arrPercentage: arrItem?.percentage || 0,
                        avgArr: avgItem?.value_aud || 0
                    };
                });

                // Add avg ARR per company for industries by count
                const enhancedCountData = countData.map(industry => ({
                    ...industry,
                    avgArrPerCompany: industry.count > 0 ? industry.value_aud / industry.count : 0
                }));

                // Add avg ARR per company for industries by ARR
                const enhancedArrData = arrData.map(industry => ({
                    ...industry,
                    avgArrPerCompany: industry.count > 0 ? industry.value_aud / industry.count : 0
                }));

                setCompanySizeData(combinedSizeData);
                setIndustriesByCount(enhancedCountData);
                setIndustriesByArr(enhancedArrData);
                setLoading(false);
            } catch (err) {
                console.error("Error fetching company and industry metrics:", err);
                setError("Failed to load industry and company size metrics");
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

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                <CircularProgress color="secondary" />
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ p: 3, color: 'error.main' }}>
                <Typography>{error}</Typography>
            </Box>
        );
    }

    return (
        <Box sx={{ mt: 4 }}>
            {/* Company Size Metrics */}
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>Company Size Distribution</Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Table>
                        <TableHead>
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                <TableCell sx={{ fontWeight: 'bold' }}>Company Size</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Customers</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>ARR</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>% of Total ARR</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Avg ARR per Customer</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {companySizeData.map((size, index) => (
                                <TableRow key={index} hover>
                                    <TableCell>{size.size}</TableCell>
                                    <TableCell align="right">{size.count}</TableCell>
                                    <TableCell align="right">{formatCurrency(size.arr)}</TableCell>
                                    <TableCell align="right">{formatPercentage(size.arrPercentage)}</TableCell>
                                    <TableCell align="right">{formatCurrency(size.avgArr)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {/* Top Industries by Count */}
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>Top Industries by Customer Count</Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Table>
                        <TableHead>
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                <TableCell sx={{ fontWeight: 'bold' }}>Industry</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Customers</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>ARR</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>% of Customers</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Avg ARR per Customer</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {industriesByCount.map((industry, index) => (
                                <TableRow key={index} hover>
                                    <TableCell>{industry.label}</TableCell>
                                    <TableCell align="right">{industry.count}</TableCell>
                                    <TableCell align="right">{formatCurrency(industry.value_aud)}</TableCell>
                                    <TableCell align="right">{formatPercentage(industry.percentage)}</TableCell>
                                    <TableCell align="right">{formatCurrency(industry.avgArrPerCompany)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {/* Top Industries by ARR */}
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>Top Industries by Annual Recurring Revenue</Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Table>
                        <TableHead>
                            <TableRow sx={{ backgroundColor: CustomColors.UIGrey200 }}>
                                <TableCell sx={{ fontWeight: 'bold' }}>Industry</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Customers</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>ARR</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>% of Total ARR</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Avg ARR per Customer</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {industriesByArr.map((industry, index) => (
                                <TableRow key={index} hover>
                                    <TableCell>{industry.label}</TableCell>
                                    <TableCell align="right">{industry.count}</TableCell>
                                    <TableCell align="right">{formatCurrency(industry.value_aud)}</TableCell>
                                    <TableCell align="right">{formatPercentage(industry.percentage)}</TableCell>
                                     <TableCell align="right">{formatCurrency(industry.avgArrPerCompany)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </Box>
    );
};

export default CompanyAndIndustryMetrics;