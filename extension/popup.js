/**
 * ROSETTA Form Filler - Popup Script
 * Handles document upload and form filling UI
 */

let selectedFile = null;
let detectedFields = [];
let extractedData = null;

// DOM elements - Initialize after DOM loads
let elements = {};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  console.log('ROSETTA popup loaded');
  
  try {
    // Initialize DOM elements
    elements = {
      fileInput: document.getElementById('file-input'),
      uploadArea: document.getElementById('upload-area'),
      fileInfo: document.getElementById('file-info'),
      fileName: document.getElementById('file-name'),
      clearFile: document.getElementById('clear-file'),
      processBtn: document.getElementById('process-btn'),
      refreshFields: document.getElementById('refresh-fields'),
      detectedFieldsList: document.getElementById('detected-fields'),
      progressSection: document.getElementById('progress-section'),
      progressFill: document.getElementById('progress-fill'),
      progressText: document.getElementById('progress-text'),
      resultsSection: document.getElementById('results-section'),
      resultsPreview: document.getElementById('results-preview'),
      fillForm: document.getElementById('fill-form'),
      editResults: document.getElementById('edit-results'),
      status: document.getElementById('status')
    };
    
    // Check if elements exist
    const missingElements = Object.entries(elements)
      .filter(([key, el]) => !el)
      .map(([key]) => key);
    
    if (missingElements.length > 0) {
      console.error('Missing DOM elements:', missingElements);
      showError('Popup initialization failed');
      return;
    }
    
    await loadSettings();
    setupEventListeners();
    
    // Detect fields after a short delay to ensure tab is ready
    setTimeout(() => {
      detectFormFields().catch(err => {
        console.warn('Initial field detection failed:', err);
      });
    }, 200);
    
  } catch (error) {
    console.error('Initialization error:', error);
    if (elements.status) {
      showError('Failed to initialize extension');
    }
  }
});

// Setup event listeners
function setupEventListeners() {
  try {
    // File upload
    elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', handleFileSelect);
    elements.clearFile.addEventListener('click', clearFile);
    
    // Drag and drop
    elements.uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      elements.uploadArea.classList.add('drag-over');
    });
    
    elements.uploadArea.addEventListener('dragleave', () => {
      elements.uploadArea.classList.remove('drag-over');
    });
    
    elements.uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      elements.uploadArea.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    });
    
    // Actions
    elements.processBtn.addEventListener('click', processDocument);
    elements.refreshFields.addEventListener('click', () => {
      detectFormFields().catch(err => console.error('Field detection failed:', err));
    });
    elements.fillForm.addEventListener('click', fillFormWithData);
    elements.editResults.addEventListener('click', showEditDialog);
    
    console.log('Event listeners setup complete');
  } catch (error) {
    console.error('Failed to setup event listeners:', error);
  }
}

// Load settings
async function loadSettings() {
  try {
    const settings = await chrome.storage.sync.get({
      apiUrl: 'http://localhost:8000',
      autoFill: false,
      language: 'en'
    });
    window.rosettaSettings = settings;
    console.log('Settings loaded:', settings);
  } catch (error) {
    console.error('Failed to load settings:', error);
    // Use defaults
    window.rosettaSettings = {
      apiUrl: 'http://localhost:8000',
      autoFill: false,
      language: 'en'
    };
  }
}

// Detect form fields on current page
async function detectFormFields() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.id) {
      console.warn('No active tab found');
      elements.detectedFieldsList.innerHTML = '<p class="placeholder">No active tab</p>';
      return;
    }
    
    // Check if we can access this tab
    if (tab.url && (tab.url.startsWith('chrome://') || tab.url.startsWith('edge://') || tab.url.startsWith('about:'))) {
      elements.detectedFieldsList.innerHTML = '<p class="error">⚠️ Cannot access browser pages</p>';
      return;
    }
    
    // Inject content script if not already injected
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js']
      });
      console.log('Content script injected');
    } catch (e) {
      console.log('Content script already injected or injection failed:', e.message);
    }
    
    // Wait a bit for script to initialize
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'detectFields'
    });
    
    if (response && response.fields && response.fields.length > 0) {
      detectedFields = response.fields;
      displayDetectedFields();
    } else {
      elements.detectedFieldsList.innerHTML = '<p class="placeholder">No form fields detected on this page</p>';
    }
  } catch (error) {
    console.error('Error detecting fields:', error);
    elements.detectedFieldsList.innerHTML = '<p class="placeholder">Navigate to a page with a form, then click "🔄 Refresh Fields"</p>';
  }
}

// Display detected fields
function displayDetectedFields() {
  if (detectedFields.length === 0) {
    elements.detectedFieldsList.innerHTML = '<p class="placeholder">No form fields detected</p>';
    return;
  }
  
  const html = `
    <div class="field-count">Found ${detectedFields.length} fields</div>
    <ul class="field-tags">
      ${detectedFields.slice(0, 10).map(field => `
        <li class="field-tag" title="${field.type}">${field.name}</li>
      `).join('')}
      ${detectedFields.length > 10 ? `<li class="field-tag more">+${detectedFields.length - 10} more</li>` : ''}
    </ul>
  `;
  
  elements.detectedFieldsList.innerHTML = html;
}

// Handle file selection
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) handleFile(file);
}

// Handle file
function handleFile(file) {
  // Validate file
  const maxSize = 10 * 1024 * 1024; // 10MB
  const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff'];
  
  if (file.size > maxSize) {
    showError('File too large. Maximum size is 10MB');
    return;
  }
  
  if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|jpe?g|png|tiff?)$/i)) {
    showError('Invalid file type. Please upload PDF, JPG, PNG, or TIFF');
    return;
  }
  
  selectedFile = file;
  
  // Update UI
  elements.uploadArea.classList.add('hidden');
  elements.fileInfo.classList.remove('hidden');
  elements.fileName.textContent = file.name;
  elements.processBtn.disabled = false;
}

// Clear file
function clearFile() {
  selectedFile = null;
  elements.fileInput.value = '';
  elements.uploadArea.classList.remove('hidden');
  elements.fileInfo.classList.add('hidden');
  elements.processBtn.disabled = true;
  elements.resultsSection.classList.add('hidden');
}

// Process document
async function processDocument() {
  if (!selectedFile) return;
  
  if (detectedFields.length === 0) {
    // Allow processing even without detected fields
    console.warn('No fields detected, will extract all data');
  }
  
  // Show progress
  elements.progressSection.classList.remove('hidden');
  elements.resultsSection.classList.add('hidden');
  elements.processBtn.disabled = true;
  
  try {
    updateProgress(10, 'Uploading document...');
    
    // Build schema from detected fields
    const schema = buildSchemaFromFields(detectedFields);
    
    console.log('Detected fields:', detectedFields);
    console.log('Built schema:', schema);
    
    // Upload to API
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('schema_json', JSON.stringify(schema));
    formData.append('language', window.rosettaSettings.language || 'en');
    formData.append('use_llm', 'true');
    
    const apiUrl = window.rosettaSettings.apiUrl || 'http://localhost:8000';
    console.log('Sending to API:', `${apiUrl}/api/v1/process`);
    
    const response = await fetch(`${apiUrl}/api/v1/process`, {
      method: 'POST',
      body: formData
    });
    
    console.log('API response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API error response:', errorText);
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    const responseData = await response.json();
    console.log('API response:', responseData);
    const { job_id } = responseData;
    
    updateProgress(30, 'Processing document...');
    
    // Poll for results
    const result = await pollJob(job_id);
    
    updateProgress(100, 'Complete!');
    
    // Display results
    console.log('Job result:', result);
    
    // Handle different result formats
    if (result.fields) {
      // Has field mapping
      console.log('Using field mapping result');
      extractedData = result.fields;
    } else if (result.extracted_text) {
      // OCR only - convert to simple format
      console.log('Converting OCR-only result to field format');
      extractedData = {};
      const texts = result.extracted_text || [];
      
      // Create a simple mapping of first N texts to field names
      const fieldNames = Object.keys(buildSchemaFromFields(detectedFields).fields);
      texts.forEach((item, index) => {
        if (index < fieldNames.length) {
          extractedData[fieldNames[index]] = {
            value: item.text || '',
            confidence: item.confidence || 0,
            not_found: false,
            uncertain: false
          };
        }
      });
    } else if (result.document_id) {
      // OCR result with document_id - fetch the document
      console.log('Fetching OCR document:', result.document_id);
      try {
        const docResponse = await fetch(`${apiUrl}/api/v1/documents/${result.document_id}`);
        const docData = await docResponse.json();
        
        console.log('Document data:', docData);
        
        extractedData = {};
        const texts = docData.extracted_text || [];
        const fieldNames = Object.keys(buildSchemaFromFields(detectedFields).fields);
        
        texts.forEach((item, index) => {
          if (index < fieldNames.length) {
            extractedData[fieldNames[index]] = {
              value: item.text || '',
              confidence: item.confidence || 0,
              not_found: false,
              uncertain: false
            };
          }
        });
      } catch (err) {
        console.error('Failed to fetch document:', err);
        extractedData = {};
      }
    } else {
      console.warn('Unknown result format:', result);
      extractedData = {};
    }
    
    console.log('Final extractedData:', extractedData);
    console.log('extractedData keys:', Object.keys(extractedData));
    displayResults();
    
    // Auto-fill if enabled
    if (window.rosettaSettings.autoFill) {
      setTimeout(() => fillFormWithData(), 500);
    }
    
  } catch (error) {
    console.error('Processing error:', error);
    showError(`Processing failed: ${error.message}`);
    elements.progressSection.classList.add('hidden');
    elements.processBtn.disabled = false;
  }
}

// Build schema from detected fields
function buildSchemaFromFields(fields) {
  const schema = {
    fields: [],  // Array of field descriptors for LLM
    split_compound_fields: true
  };
  
  // If no fields detected, use common default fields
  if (!fields || fields.length === 0) {
    console.log('No fields detected, using default schema');
    schema.fields = [
      {name: 'firstName', type: 'string', label: 'First Name'},
      {name: 'lastName', type: 'string', label: 'Last Name'},
      {name: 'email', type: 'email', label: 'Email'},
      {name: 'phone', type: 'phone', label: 'Phone'}
    ];
    return schema;
  }
  
  // Build detailed field descriptors for LLM
  for (const field of fields) {
    const contextParts = [
      field.label,
      field.placeholder,
      field.ariaLabel,
      field.autocomplete,
      field.nearbyText,
      field.formContext,
      field.id,
      field.title
    ].filter(x => x && x.trim());
    
    schema.fields.push({
      name: field.name,
      type: mapFieldType(field.type),
      required: field.required || false,
      label: field.label || '',
      placeholder: field.placeholder || '',
      ariaLabel: field.ariaLabel || '',
      autocomplete: field.autocomplete || '',
      currentValue: field.currentValue || '',
      // Rich context for LLM reasoning
      context: contextParts.join(' | '),
      nearbyText: field.nearbyText || '',
      formContext: field.formContext || ''
    });
  }
  
  console.log('Built schema with', schema.fields.length, 'fields');
  console.log('Sample field context:', schema.fields[0]?.context);
  return schema;
}

// Map HTML input types to API field types
function mapFieldType(htmlType) {
  const typeMap = {
    'email': 'email',
    'tel': 'phone',
    'number': 'number',
    'date': 'date',
    'url': 'url'
  };
  
  return typeMap[htmlType] || 'string';
}

// Poll job status
async function pollJob(jobId, maxAttempts = 60) {
  const apiUrl = window.rosettaSettings.apiUrl || 'http://localhost:8000';
  
  console.log('Polling job:', jobId);
  
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const response = await fetch(`${apiUrl}/api/v1/jobs/${jobId}`);
    const job = await response.json();
    
    console.log(`Job status (attempt ${i + 1}):`, job);
    
    if (job.status === 'completed') {
      console.log('Job completed! Result:', job.result);
      return job.result;
    } else if (job.status === 'failed') {
      console.error('Job failed:', job.error);
      throw new Error(job.error || 'Processing failed');
    }
    
    // Update progress
    const progress = 30 + (job.progress || 0) * 0.7;
    updateProgress(progress, `Processing... ${job.progress || 0}%`);
  }
  
  throw new Error('Job timeout');
}

// Update progress
function updateProgress(percent, text) {
  elements.progressFill.style.width = `${percent}%`;
  elements.progressText.textContent = text;
}

// Display results
function displayResults() {
  if (!extractedData || Object.keys(extractedData).length === 0) {
    elements.progressSection.classList.add('hidden');
    showError('No data extracted from document');
    return;
  }
  
  elements.progressSection.classList.add('hidden');
  elements.resultsSection.classList.remove('hidden');
  
  console.log('Displaying results for:', extractedData);
  
  const html = Object.entries(extractedData).map(([fieldName, fieldData]) => {
    const icon = fieldData.not_found ? '❌' : 
                 fieldData.uncertain ? '⚠️' : '✅';
    const valueClass = fieldData.not_found ? 'value-missing' : 
                       fieldData.uncertain ? 'value-uncertain' : 'value-found';
    
    return `
      <div class="result-item">
        <div class="result-header">
          <span class="result-icon">${icon}</span>
          <span class="result-name">${fieldName}</span>
          <span class="result-confidence">${(fieldData.confidence * 100).toFixed(0)}%</span>
        </div>
        <div class="result-value ${valueClass}">
          ${fieldData.value || '(not found)'}
        </div>
      </div>
    `;
  }).join('');
  
  elements.resultsPreview.innerHTML = html;
}

// Fill form with extracted data
async function fillFormWithData() {
  if (!extractedData) {
    showError('No data to fill');
    return;
  }
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.id) {
      showError('No active tab found');
      return;
    }
    
    console.log('Sending fill command to tab:', tab.id);
    console.log('Data to fill:', extractedData);
    
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'fillForm',
      data: extractedData
    });
    
    console.log('Fill response:', response);
    
    if (response && response.success) {
      showSuccess('Form filled successfully!');
      
      // Close popup after short delay
      setTimeout(() => window.close(), 1500);
    } else {
      showError('Failed to fill form - content script may not be loaded');
    }
    
  } catch (error) {
    console.error('Error filling form:', error);
    showError(`Failed to fill form: ${error.message}`);
  }
}

// Show edit dialog
function showEditDialog() {
  // TODO: Implement edit dialog
  alert('Edit functionality coming soon!');
}

// Show error
function showError(message) {
  if (!elements.status) {
    console.error('Error (no status element):', message);
    return;
  }
  
  elements.status.className = 'status error';
  elements.status.querySelector('.status-icon').textContent = '❌';
  elements.status.querySelector('.status-text').textContent = message;
  elements.status.classList.remove('hidden');
  
  setTimeout(() => elements.status.classList.add('hidden'), 5000);
}

// Show success
function showSuccess(message) {
  if (!elements.status) {
    console.log('Success (no status element):', message);
    return;
  }
  
  elements.status.className = 'status success';
  elements.status.querySelector('.status-icon').textContent = '✅';
  elements.status.querySelector('.status-text').textContent = message;
  elements.status.classList.remove('hidden');
  
  setTimeout(() => elements.status.classList.add('hidden'), 3000);
}
