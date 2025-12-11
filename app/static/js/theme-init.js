// Uptimo Theme Initialization Script
// This script runs immediately to prevent white flash on page load
(function() {
    // Get theme from cookie or system preference
    function getThemeFromCookie() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'uptimo_theme') {
                return decodeURIComponent(value);
            }
        }
        return null;
    }
    
    function getSystemThemePreference() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }
    
    // Apply theme immediately before CSS loads
    const savedTheme = getThemeFromCookie();
    const systemPreference = getSystemThemePreference();
    const theme = savedTheme || systemPreference;
    
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
})();