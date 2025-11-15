/**
 * ROSETTA Form Filler - Options Page Script
 */

const DEFAULT_SETTINGS = {
  apiUrl: 'http://localhost:8000',
  autoFill: false,
  language: 'en',
  performanceMode: 'balanced',
  preprocessing: true
};

// DOM elements
const elements = {
  apiUrl: document.getElementById('apiUrl'),
  language: document.getElementById('language'),
  performanceMode: document.getElementById('performanceMode'),
  preprocessing: document.getElementById('preprocessing'),
  autoFill: document.getElementById('autoFill'),
  connectionStatus: document.getElementById('connectionStatus'),
  testConnection: document.getElementById('testConnection'),
  saveBtn: document.getElementById('saveBtn'),
  resetBtn: document.getElementById('resetBtn'),
  saveStatus: document.getElementById('saveStatus')
};

// Load settings on page load
document.addEventListener('DOMContentLoaded', loadSettings);

// Event listeners
elements.saveBtn.addEventListener('click', saveSettings);
elements.resetBtn.addEventListener('click', resetSettings);
elements.testConnection.addEventListener('click', testConnection);

/**
 * Load settings from storage
 */
async function loadSettings() {
  try {
    const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
    
    elements.apiUrl.value = settings.apiUrl;
    elements.language.value = settings.language;
    elements.performanceMode.value = settings.performanceMode;
    elements.preprocessing.checked = settings.preprocessing;
    elements.autoFill.checked = settings.autoFill;
    
    console.log('Settings loaded:', settings);
  } catch (error) {
    console.error('Error loading settings:', error);
  }
}

/**
 * Save settings to storage
 */
async function saveSettings() {
  try {
    const settings = {
      apiUrl: elements.apiUrl.value.trim(),
      language: elements.language.value,
      performanceMode: elements.performanceMode.value,
      preprocessing: elements.preprocessing.checked,
      autoFill: elements.autoFill.checked
    };
    
    await chrome.storage.sync.set(settings);
    
    console.log('Settings saved:', settings);
    showSaveStatus();
    
  } catch (error) {
    console.error('Error saving settings:', error);
    alert('Failed to save settings');
  }
}

/**
 * Reset settings to defaults
 */
async function resetSettings() {
  if (confirm('Reset all settings to defaults?')) {
    try {
      await chrome.storage.sync.set(DEFAULT_SETTINGS);
      await loadSettings();
      showSaveStatus();
    } catch (error) {
      console.error('Error resetting settings:', error);
    }
  }
}

/**
 * Test API connection
 */
async function testConnection() {
  const apiUrl = elements.apiUrl.value.trim();
  
  if (!apiUrl) {
    alert('Please enter an API URL');
    return;
  }
  
  // Update status
  updateConnectionStatus('testing', 'Testing...');
  elements.testConnection.disabled = true;
  
  try {
    const response = await fetch(`${apiUrl}/api/v1/health`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.status === 'healthy') {
      updateConnectionStatus('connected', 'Connected ✓');
      
      // Show additional info
      setTimeout(() => {
        const info = `OCR: ${data.ocr_loaded ? '✓' : '✗'}, LLM: ${data.llm_loaded ? '✓' : '✗'}`;
        alert(`Connection successful!\n\n${info}\nVersion: ${data.version}`);
      }, 500);
    } else {
      throw new Error('API unhealthy');
    }
    
  } catch (error) {
    console.error('Connection test failed:', error);
    updateConnectionStatus('disconnected', 'Connection Failed');
    alert(`Connection failed: ${error.message}\n\nMake sure the ROSETTA API is running on ${apiUrl}`);
  } finally {
    elements.testConnection.disabled = false;
  }
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(status, text) {
  elements.connectionStatus.className = 'status-indicator';
  
  if (status === 'connected') {
    elements.connectionStatus.classList.add('status-connected');
    elements.connectionStatus.innerHTML = '🟢 ' + text;
  } else if (status === 'disconnected') {
    elements.connectionStatus.classList.add('status-disconnected');
    elements.connectionStatus.innerHTML = '🔴 ' + text;
  } else if (status === 'testing') {
    elements.connectionStatus.classList.add('status-testing');
    elements.connectionStatus.innerHTML = '🟡 ' + text;
  }
}

/**
 * Show save status message
 */
function showSaveStatus() {
  elements.saveStatus.classList.add('show');
  
  setTimeout(() => {
    elements.saveStatus.classList.remove('show');
  }, 3000);
}

// Test connection on load if API URL is set
loadSettings().then(() => {
  if (elements.apiUrl.value) {
    testConnection();
  }
});
