// src/components/common/CountryFlag.jsx
import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';
import { CustomColors } from '../../theme';

/**
 * A reliable country flag component using CDN images with consistent sizing
 */
const CountryFlag = ({
                         countryCode,
                         name,
                         size = 24,
                         className = '',
                         style = {},
                         showName = false
                     }) => {
    const [imageFailed, setImageFailed] = useState(false);
    const displayName = name || countryCode;

    // Set a fixed container size, slightly larger than the flag itself
    const containerSize = {
        width: size,
        height: Math.round(size * 0.75)
    };

    // If no country code or image failed, show the code in a styled box
    if (!countryCode || imageFailed) {
        return (
            <Box
                className={className}
                sx={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    ...style
                }}
            >
                <Box
                    sx={{
                        width: containerSize.width,
                        height: containerSize.height,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}
                >
                    <Typography
                        component="span"
                        sx={{
                            display: 'inline-block',
                            backgroundColor: CustomColors.UIGrey200,
                            color: CustomColors.UIGrey800,
                            fontWeight: 'bold',
                            borderRadius: '4px',
                            padding: '2px 6px',
                            fontSize: `${size/16}rem`,
                            textAlign: 'center',
                            border: `1px solid ${CustomColors.UIGrey300}`
                        }}
                    >
                        {countryCode || '??'}
                    </Typography>
                </Box>
                {showName && <span style={{ marginLeft: '8px' }}>{displayName}</span>}
            </Box>
        );
    }

    // Default - use image from CDN in fixed container
    return (
        <Box
            className={className}
            sx={{
                display: 'inline-flex',
                alignItems: 'center',
                ...style
            }}
        >
            <Box
                sx={{
                    width: containerSize.width,
                    height: containerSize.height,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden'
                }}
            >
                <img
                    src={`https://flagcdn.com/${countryCode.toLowerCase()}.svg`}
                    alt={`${displayName} flag`}
                    style={{
                        maxWidth: '100%',
                        maxHeight: '100%',
                        objectFit: 'contain',
                        border: `1px solid ${CustomColors.UIGrey300}`,
                        borderRadius: '2px',
                    }}
                    onError={() => setImageFailed(true)}
                />
            </Box>
            {showName && <span style={{ marginLeft: '8px' }}>{displayName}</span>}
        </Box>
    );
};

export default CountryFlag;