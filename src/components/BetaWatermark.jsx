// src/components/BetaWatermark.jsx
import React from 'react';
import { Box } from '@mui/material';
import { CustomColors } from '../theme';

const BetaWatermark = () => {
    return (
        <Box
            sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                pointerEvents: 'none', // Allow clicking through
                zIndex: 1000,
                overflow: 'hidden',
                opacity: 0.15, // Subtle but visible
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
            }}
        >
            <Box
                sx={{
                    position: 'absolute',
                    fontSize: '120px',
                    fontWeight: 'bold',
                    color: CustomColors.DeepSkyBlue,
                    transform: 'rotate(-30deg)',
                    userSelect: 'none',
                    letterSpacing: '5px',
                    textShadow: '1px 1px 2px rgba(0,0,0,0.3)',
                }}
            >
                BETA
            </Box>
        </Box>
    );
};

export default BetaWatermark;