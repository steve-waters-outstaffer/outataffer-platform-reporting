// src/utils/countryFlags.js

/**
 * Get a URL for a country flag image
 * @param {string} countryCode - The ISO 2-letter country code
 * @param {number} width - Optional width of the flag image
 * @returns {string} URL to the flag image
 */
export const getCountryFlagUrl = (countryCode, width = 40) => {
    if (!countryCode) return null;

    // Normalize country code (ensure it's lowercase for the CDN)
    const normalizedCode = countryCode.toLowerCase();

    // Use flagcdn.com which provides reliable flag images
    return `https://flagcdn.com/w${width}/${normalizedCode}.png`;
};

/**
 * Get a country flag emoji from country code
 * @param {string} countryCode - The ISO 2-letter country code
 * @returns {string} The flag emoji or a globe emoji as fallback
 */
export const getCountryFlagEmoji = (countryCode) => {
    if (!countryCode) return '🌎'; // Default globe emoji

    // Special case mapping for some countries
    const specialCases = {
        'UK': 'GB', // Convert UK to GB for flag purposes
        'UAE': 'AE',
        // Add other special cases as needed
    };

    // Normalize and ensure we use just 2 characters
    const normalized = (specialCases[countryCode.toUpperCase()] || countryCode).toUpperCase().slice(0, 2);

    try {
        // Convert to regional indicator symbols
        // Each letter is converted to Regional Indicator Symbol Letter by adding 127397 to its Unicode value
        const codePoints = normalized
            .split('')
            .map(char => 127397 + char.charCodeAt(0));

        return String.fromCodePoint(...codePoints);
    } catch (err) {
        console.warn(`Could not generate flag emoji for country: ${countryCode}`, err);
        return '🌎';
    }
};

/**
 * Get a simple string representation for the country with its flag
 * @param {string} countryCode - The ISO 2-letter country code
 * @param {string} countryName - The country name
 * @returns {string} String with flag emoji and country name
 */
export const getCountryWithFlag = (countryCode, countryName) => {
    if (!countryCode || !countryName) return countryName || 'Unknown';
    return `${getCountryFlagEmoji(countryCode)} ${countryName}`;
};