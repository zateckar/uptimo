// OIDC Provider configuration type toggle
document.addEventListener('DOMContentLoaded', function() {
    const configType = document.getElementById('configType');
    const discoveryConfig = document.getElementById('discoveryConfig');
    const manualConfig = document.getElementById('manualConfig');
    
    function toggleConfigSections() {
        if (configType && discoveryConfig && manualConfig) {
            if (configType.value === 'discovery') {
                discoveryConfig.classList.remove('hidden');
                manualConfig.classList.add('hidden');
            } else {
                discoveryConfig.classList.add('hidden');
                manualConfig.classList.remove('hidden');
            }
        }
    }
    
    if (configType) {
        configType.addEventListener('change', toggleConfigSections);
        // Set initial state
        toggleConfigSections();
    }
});