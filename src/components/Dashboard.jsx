// src/components/Dashboard.jsx
import React from 'react';
import BetaWatermark from './BetaWatermark';
import { useNavigate } from 'react-router-dom';
import {
    AppBar,
    Toolbar,
    Typography,
    Button,
    Container,
    Paper,
    Box,
    Card,
    CardContent,
    CardActions,
    Grid
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { logoutUser } from '../services/AuthService.js';
import { CustomColors } from '../theme';
import BarChartIcon from '@mui/icons-material/BarChart';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';
import BusinessIcon from '@mui/icons-material/Business';
import MonetizationOnIcon from '@mui/icons-material/MonetizationOn';
import PublicIcon from '@mui/icons-material/Public';



const Dashboard = () => {
    const { currentUser } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        try {
            await logoutUser();
            navigate('/login');
        } catch (error) {
            console.error("Logout error:", error);
        }
    };

    const dashboards = [
        {
            title: 'Revenue Dashboard',
            description: 'Monitor MRR, ARR, and revenue breakdown by service type',
            icon: <MonetizationOnIcon sx={{ fontSize: 48, color: CustomColors.MidnightBlue }} />,
            path: '/revenue-dashboard',
            available: true
        },
        {
            title: 'Plan & Add-on Analytics',
            description: 'Breakdown of hardware, software, and memberships',
            icon: <PublicIcon sx={{ fontSize: 48, color: CustomColors.Purple }} />,
            path: '/addons-dashboard',
            available: true
        },
        {
            title: 'Requisitions Dashboard',
            description: 'Monthly requisition metrics and open positions',
            icon: <BarChartIcon sx={{ fontSize: 48, color: CustomColors.DeepSkyBlue }} />,
            path: '/requisitions-dashboard',
            available: true
        },
        {
            title: 'Health Insurance Analytics',
            description: 'Health insurance uptake and distribution',
            icon: <PeopleAltIcon sx={{ fontSize: 48, color: CustomColors.Cobalt }} />,
            path: '/health-dashboard',
            available: true
        },
        {
            title: 'Customer Analytics',
            description: 'Customer and Company metrics and analysis',
            icon: <BusinessIcon sx={{ fontSize: 48, color: CustomColors.Meadow }} />,
            path: '/customer-dashboard',
            available: true // Change this from false to true
        },
        {
            title: 'Geographic Distribution',
            description: 'Country-level metrics and geographic analysis',
            icon: <PublicIcon sx={{ fontSize: 48, color: CustomColors.SlateBlue }} />,
            path: '/geographic-dashboard',
            available: true
        },

    ];

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
            <BetaWatermark />
            <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                    <Typography variant="h4" component="h1" gutterBottom>
                        Management Dashboard
                    </Typography>
                    <Typography variant="body" color="text.secondary" gutterBottom>
                        Welcome to the Outstaffer management reporting system. Select a dashboard to view detailed metrics.
                    </Typography>
                    <Box sx={{ mb: 2 }}></Box> {/* Add spacing between paragraphs */}
                    <Typography variant="h4" color="text.secondary" align={"center"}>
                        This dashboard is in beta and may display incomplete information, some data may be missing or out of date. Please do not rely on this dashboard for critical decisions or reporting purposes.
                    </Typography>
                </Paper>

                <Grid container spacing={3}>
                    {dashboards.map((dashboard, index) => (
                        <Grid item xs={12} sm={6} md={4} key={index}>
                            <Card sx={{
                                height: '100%',
                                display: 'flex',
                                flexDirection: 'column',
                                opacity: dashboard.available ? 1 : 0.7,
                                transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                                '&:hover': dashboard.available ? {
                                    transform: 'translateY(-5px)',
                                    boxShadow: '0px 6px 12px rgba(0, 0, 0, 0.15)'
                                } : {}
                            }}>
                                <CardContent sx={{ flexGrow: 1 }}>
                                    <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                                        {dashboard.icon}
                                    </Box>
                                    <Typography variant="h5" component="h2" align="center" gutterBottom>
                                        {dashboard.title}
                                    </Typography>
                                    <Typography variant="body" color="text.secondary" align="center">
                                        {dashboard.description}
                                    </Typography>
                                </CardContent>
                                <CardActions>
                                    <Button
                                        fullWidth
                                        variant={dashboard.available ? "contained" : "outlined"}
                                        color="primary"
                                        onClick={() => dashboard.available ? navigate(dashboard.path) : null}
                                        disabled={!dashboard.available}
                                    >
                                        {dashboard.available ? 'View Dashboard' : 'Coming Soon'}
                                    </Button>
                                </CardActions>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            </Container>
        </Box>
    );
};

export default Dashboard;