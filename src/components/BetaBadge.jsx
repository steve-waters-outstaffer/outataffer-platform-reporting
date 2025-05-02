// src/components/BetaBadge.jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { CustomColors } from '../theme';

const BetaBadge = ({ position = 'top-left' }) => {
    // Define position styles based on the chosen position
    const positionStyles = {
        'top-right': { top: 20, right: 20 },
        'top-left': { top: 20, left: 20 },
        'bottom-right': { bottom: 700, right: 1000 },
        'bottom-left': { bottom: 20, left: 20 },
    };

    return (
        <Box
            sx={{
                position: 'fixed',
                zIndex: 9999, // Ensure it's above everything
                ...positionStyles[position],
                transform: 'rotate(-15deg)', // Slight rotation for a "stamp" effect
                backgroundColor: 'rgba(255, 0, 0, 0.7)', // Semi-transparent red
                padding: '4px 12px',
                borderRadius: '4px',
                boxShadow: '0 2px 10px rgba(0, 0, 0, 0.2)',
                border: '1px solid rgba(255, 0, 0, 0.9)',
                pointerEvents: 'none', // So it doesn't interfere with clicking
            }}
        >
            <Typography
                variant="h6"
                sx={{
                    color: 'white',
                    fontWeight: 'bold',
                    letterSpacing: '1px',
                    textTransform: 'uppercase',
                    fontSize: '120px',
                    lineHeight: 1,
                }}
            >
                Beta
            </Typography>
        </Box>
    );
};

export default BetaBadge;