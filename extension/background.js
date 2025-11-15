/**
 * ROSETTA Form Filler - Background Service Worker
 * Handles extension lifecycle and communication
 */

// Default settings
const DEFAULT_SETTINGS = {
  apiUrl: 'http://localhost:8000',
  autoFill: false,
  language: 'en',
  performanceMode: 'balanced',
  preprocessing: true
};

// Initialize extension
chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === 'install') {
    // Set default settings
    await chrome.storage.sync.set(DEFAULT_SETTINGS);
    
    console.log('ROSETTA Form Filler installed');
    
    // Open welcome page
    chrome.tabs.create({
      url: chrome.runtime.getURL('options.html')
    });
  } else if (details.reason === 'update') {
    console.log('ROSETTA Form Filler updated to', chrome.runtime.getManifest().version);
  }
});

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
  // Popup is handled automatically by manifest
  console.log('Extension clicked on tab:', tab.id);
});

// Handle messages from content scripts and popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSettings') {
    chrome.storage.sync.get(DEFAULT_SETTINGS, (settings) => {
      sendResponse(settings);
    });
    return true;
  }
  
  if (request.action === 'saveSettings') {
    chrome.storage.sync.set(request.settings, () => {
      sendResponse({ success: true });
    });
    return true;
  }
  
  if (request.action === 'testConnection') {
    testAPIConnection(request.apiUrl)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

/**
 * Test API connection
 */
async function testAPIConnection(apiUrl) {
  try {
    const response = await fetch(`${apiUrl}/api/v1/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    return {
      success: true,
      status: data.status,
      ocrLoaded: data.ocr_loaded,
      llmLoaded: data.llm_loaded
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

// Log extension startup
console.log('ROSETTA Form Filler background service worker started');
