/**
 * Recording functionality for Test Automation Platform
 * Handles UI test recording workflow
 */

window.RecordingManager = {
    isRecording: false,
    statusCheckInterval: null,
    csrfToken: null,
    currentSession: null,
    
    /**
     * Initialize recording manager
     */
    init: function() {
        this.csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
        this.setupEventListeners();
        this.checkExistingSession();
    },
    
    /**
     * Setup event listeners
     */
    setupEventListeners: function() {
        const recordingForm = document.getElementById('recordingForm');
        if (recordingForm) {
            recordingForm.addEventListener('submit', this.handleStartRecording.bind(this));
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
        
        // Page visibility change
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        
        // Before unload warning if recording is active
        window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
    },
    
    /**
     * Check for existing recording session
     */
    checkExistingSession: function() {
        this.makeRequest('/record/status', 'GET')
            .then(data => {
                if (data.is_recording) {
                    this.showRecordingStatus(data);
                    this.startStatusPolling();
                }
            })
            .catch(error => {
                console.warn('Failed to check recording status:', error);
            });
    },
    
    /**
     * Handle start recording form submission
     */
    handleStartRecording: function(e) {
        e.preventDefault();
        
        const form = e.currentTarget;
        const formData = new FormData(form);
        
        // Validate form
        if (!this.validateForm(form)) {
            return;
        }
        
        // Disable form and show loading
        this.setFormLoading(form, true);
        
        this.makeRequest('/record/start', 'POST', formData)
            .then(data => {
                if (data.success) {
                    this.currentSession = {
                        script_id: data.script_id,
                        script_name: formData.get('script_name'),
                        browser_type: formData.get('browser_type'),
                        started_at: new Date().toISOString()
                    };
                    
                    this.showRecordingStatus({
                        is_recording: true,
                        session_info: this.currentSession
                    });
                    
                    this.startStatusPolling();
                    TestApp.utils.showToast(data.message, 'success');
                } else {
                    TestApp.utils.showToast(data.error, 'danger');
                    this.setFormLoading(form, false);
                }
            })
            .catch(error => {
                TestApp.utils.showToast('Failed to start recording. Please try again.', 'danger');
                this.setFormLoading(form, false);
            });
    },
    
    /**
     * Stop recording
     */
    stopRecording: function() {
        // Always try to stop, even if polling missed session
        if (!this.isRecording && !this.currentSession) {
            TestApp.utils.showToast('No active recording session found.', 'danger');
            return;
        }
        this._pendingStop = true;
        const formData = new FormData();
        formData.append('csrf_token', this.csrfToken);
        this.makeRequest('/record/stop', 'POST', formData)
            .then(data => {
                this._pendingStop = false;
                if (data.success) {
                    this.showCompletionStatus(data);
                    this.stopStatusPolling();
                    TestApp.utils.showToast(data.message, 'success');
                    // Redirect after a delay
                    if (data.redirect_url) {
                        setTimeout(() => {
                            window.location.href = data.redirect_url;
                        }, 3000);
                    }
                } else {
                    TestApp.utils.showToast(data.error, 'danger');
                }
            })
            .catch(error => {
                this._pendingStop = false;
                TestApp.utils.showToast('Failed to stop recording. Please try again.', 'danger');
            });
    },
    
    /**
     * Cancel recording
     */
    cancelRecording: function() {
        if (!confirm('Are you sure you want to cancel the recording? All recorded actions will be lost.')) {
            return;
        }
        if (!this.isRecording && !this.currentSession) {
            TestApp.utils.showToast('No active recording session found.', 'danger');
            return;
        }
        this._pendingStop = true;
        const formData = new FormData();
        formData.append('csrf_token', this.csrfToken);
        this.makeRequest('/record/cancel', 'POST', formData)
            .then(data => {
                this._pendingStop = false;
                if (data.success) {
                    this.resetToInitialState();
                    TestApp.utils.showToast(data.message, 'info');
                } else {
                    TestApp.utils.showToast(data.error, 'danger');
                }
            })
            .catch(error => {
                this._pendingStop = false;
                TestApp.utils.showToast('Failed to cancel recording.', 'danger');
            });
    },
    
    /**
     * Start status polling
     */
    startStatusPolling: function() {
        if (this.statusCheckInterval) return;
        
        this.isRecording = true;
        this.statusCheckInterval = setInterval(() => {
            this.checkRecordingStatus();
        }, 3000);
    },
    
    /**
     * Stop status polling
     */
    stopStatusPolling: function() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }
        this.isRecording = false;
    },
    
    /**
     * Check recording status
     */
    checkRecordingStatus: function() {
        this.makeRequest('/record/status', 'GET')
            .then(data => {
                // Only reset UI if session is truly ended by user action
                if (!data.is_recording && this.isRecording && !this._pendingStop) {
                    // Do not reset UI unless user clicked stop/cancel
                    return;
                } else if (data.is_recording) {
                    this.updateRecordingStatus(data);
                }
            })
            .catch(error => {
                // Do not reset UI on polling error, just log
                console.warn('Failed to check recording status:', error);
            });
    },
    
    /**
     * Show recording status UI
     */
    showRecordingStatus: function(data) {
        const form = document.getElementById('recordingForm');
        const statusDiv = document.getElementById('recordingStatus');
        
        if (form) form.style.display = 'none';
        if (statusDiv) {
            statusDiv.classList.remove('d-none');
            
            // Update session info
            if (data.session_info) {
                const info = data.session_info;
                document.getElementById('recordingScript').textContent = info.script_name;
                document.getElementById('recordingBrowser').textContent = info.browser_type;
                document.getElementById('recordingStarted').textContent = 
                    new Date(info.started_at).toLocaleString();
            }
        }
        
        this.isRecording = true;
    },
    
    /**
     * Show completion status UI
     */
    showCompletionStatus: function(data) {
        const statusDiv = document.getElementById('recordingStatus');
        const completionDiv = document.getElementById('completionStatus');
        
        if (statusDiv) statusDiv.style.display = 'none';
        if (completionDiv) {
            completionDiv.classList.remove('d-none');
            
            // Enable view script button after conversion
            setTimeout(() => {
                const viewBtn = document.getElementById('viewScriptBtn');
                if (viewBtn && data.script_id) {
                    viewBtn.disabled = false;
                    viewBtn.onclick = () => {
                        if (data.redirect_url) {
                            window.location.href = data.redirect_url;
                        }
                    };
                }
            }, 2000);
        }
        
        this.isRecording = false;
    },
    
    /**
     * Update recording status display
     */
    updateRecordingStatus: function(data) {
        // Update duration if needed
        if (data.session_info && data.session_info.started_at) {
            const startTime = new Date(data.session_info.started_at);
            const duration = Math.floor((new Date() - startTime) / 1000);
            
            let durationElement = document.getElementById('recordingDuration');
            if (!durationElement) {
                durationElement = document.createElement('div');
                durationElement.id = 'recordingDuration';
                durationElement.className = 'mt-2 text-muted small';
                document.getElementById('recordingStatus').appendChild(durationElement);
            }
            
            durationElement.innerHTML = `<strong>Duration:</strong> ${TestApp.utils.formatDuration(duration)}`;
        }
    },
    
    /**
     * Reset to initial state
     */
    resetToInitialState: function() {
        const form = document.getElementById('recordingForm');
        const statusDiv = document.getElementById('recordingStatus');
        const completionDiv = document.getElementById('completionStatus');
        
        if (form) {
            form.style.display = 'block';
            this.setFormLoading(form, false);
        }
        
        if (statusDiv) statusDiv.classList.add('d-none');
        if (completionDiv) completionDiv.classList.add('d-none');
        
        this.stopStatusPolling();
        this.currentSession = null;
    },
    
    /**
     * Validate recording form
     */
    validateForm: function(form) {
        const projectId = form.querySelector('[name="project_id"]').value;
        const scriptName = form.querySelector('[name="script_name"]').value.trim();
        
        if (!projectId) {
            TestApp.utils.showToast('Please select a project.', 'warning');
            return false;
        }
        
        if (!scriptName) {
            TestApp.utils.showToast('Please enter a script name.', 'warning');
            return false;
        }
        
        if (scriptName.length < 3) {
            TestApp.utils.showToast('Script name must be at least 3 characters.', 'warning');
            return false;
        }
        
        // Check for valid script name characters
        if (!/^[a-zA-Z0-9\s_-]+$/.test(scriptName)) {
            TestApp.utils.showToast('Script name can only contain letters, numbers, spaces, dashes, and underscores.', 'warning');
            return false;
        }
        
        return true;
    },
    
    /**
     * Set form loading state
     */
    setFormLoading: function(form, isLoading) {
        const submitBtn = form.querySelector('button[type="submit"]');
        const inputs = form.querySelectorAll('input, select, textarea');
        
        if (isLoading) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting Recording...';
            inputs.forEach(input => input.disabled = true);
        } else {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-video me-2"></i>Start Recording';
            inputs.forEach(input => input.disabled = false);
        }
    },
    
    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts: function(e) {
        // Ctrl+Shift+R to start/stop recording
        if (e.ctrlKey && e.shiftKey && e.key === 'R') {
            e.preventDefault();
            
            if (this.isRecording) {
                this.stopRecording();
            } else {
                const form = document.getElementById('recordingForm');
                if (form && form.style.display !== 'none') {
                    form.dispatchEvent(new Event('submit'));
                }
            }
        }
        
        // Escape to cancel recording
        if (e.key === 'Escape' && this.isRecording) {
            this.cancelRecording();
        }
    },
    
    /**
     * Handle visibility change
     */
    handleVisibilityChange: function() {
        if (document.hidden && this.isRecording) {
            // Page is hidden while recording, reduce polling frequency
            this.stopStatusPolling();
            setTimeout(() => {
                if (!document.hidden && this.isRecording) {
                    this.startStatusPolling();
                }
            }, 1000);
        } else if (!document.hidden && this.isRecording && !this.statusCheckInterval) {
            // Page is visible again, resume polling
            this.startStatusPolling();
        }
    },
    
    /**
     * Handle before unload
     */
    handleBeforeUnload: function(e) {
        if (this.isRecording) {
            const message = 'Recording is in progress. Are you sure you want to leave? All recorded actions will be lost.';
            e.returnValue = message;
            return message;
        }
    },
    
    /**
     * Make HTTP request with error handling
     */
    makeRequest: function(url, method, body = null) {
        const options = {
            method: method,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        if (body) {
            options.body = body;
        }
        
        return fetch(url, options)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            });
    }
};

// Global functions for HTML onclick handlers
function stopRecording() {
    RecordingManager.stopRecording();
}

function cancelRecording() {
    RecordingManager.cancelRecording();
}

function viewScript() {
    const btn = document.getElementById('viewScriptBtn');
    if (btn && btn.onclick) {
        btn.onclick();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    RecordingManager.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    RecordingManager.stopStatusPolling();
});
