/**
 * Main application JavaScript
 * Handles common functionality across the Test Automation Platform
 */

// Global application object
window.TestApp = {
    // Configuration
    config: {
        csrf_token: null,
        polling_interval: 5000,
        toast_duration: 5000
    },
    
    // Utilities
    utils: {},
    
    // Components
    components: {},
    
    // Initialize application
    init: function() {
        this.utils.initCSRF();
        this.utils.initTooltips();
        this.utils.initConfirmations();
        this.utils.initAutoRefresh();
        console.log('Test Automation Platform initialized');
    }
};

// Utility functions
TestApp.utils = {
    /**
     * Initialize CSRF token from meta tag or form
     */
    initCSRF: function() {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            TestApp.config.csrf_token = csrfMeta.getAttribute('content');
        }
    },
    
    /**
     * Initialize Bootstrap tooltips
     */
    initTooltips: function() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },
    
    /**
     * Initialize confirmation dialogs
     */
    initConfirmations: function() {
        document.addEventListener('click', function(e) {
            const confirmBtn = e.target.closest('[data-confirm]');
            if (confirmBtn) {
                const message = confirmBtn.getAttribute('data-confirm');
                if (!confirm(message)) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            }
        });
    },
    
    /**
     * Initialize auto-refresh for elements with data-auto-refresh
     */
    initAutoRefresh: function() {
        const autoRefreshElements = document.querySelectorAll('[data-auto-refresh]');
        autoRefreshElements.forEach(function(element) {
            const interval = parseInt(element.getAttribute('data-auto-refresh')) || 30000;
            const url = element.getAttribute('data-refresh-url') || window.location.href;
            
            setInterval(function() {
                TestApp.utils.refreshElement(element, url);
            }, interval);
        });
    },
    
    /**
     * Refresh element content via AJAX
     */
    refreshElement: function(element, url) {
        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newElement = doc.querySelector(`#${element.id}`);
            
            if (newElement) {
                element.innerHTML = newElement.innerHTML;
            }
        })
        .catch(error => {
            console.warn('Failed to refresh element:', error);
        });
    },
    
    /**
     * Show toast notification
     */
    showToast: function(message, type = 'info', duration = null) {
        duration = duration || TestApp.config.toast_duration;
        
        const toastContainer = this.getToastContainer();
        const toastId = 'toast-' + Date.now();
        
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${this.escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: duration
        });
        
        bsToast.show();
        
        // Clean up after toast is hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
        
        return bsToast;
    },
    
    /**
     * Get or create toast container
     */
    getToastContainer: function() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    },
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    /**
     * Format duration in seconds to human readable format
     */
    formatDuration: function(seconds) {
        if (!seconds) return '-';
        
        if (seconds < 60) {
            return Math.round(seconds * 10) / 10 + 's';
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.round(seconds % 60);
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    },
    
    /**
     * Format timestamp to relative time
     */
    formatRelativeTime: function(timestamp) {
        const now = new Date();
        const date = new Date(timestamp);
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) {
            return 'just now';
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else {
            const days = Math.floor(diffInSeconds / 86400);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        }
    },
    
    /**
     * Make AJAX request with CSRF token
     */
    request: function(url, options = {}) {
        options.headers = options.headers || {};
        
        if (TestApp.config.csrf_token) {
            options.headers['X-CSRFToken'] = TestApp.config.csrf_token;
        }
        
        if (options.method && options.method.toLowerCase() !== 'get') {
            options.headers['X-Requested-With'] = 'XMLHttpRequest';
        }
        
        return fetch(url, options);
    },
    
    /**
     * Debounce function execution
     */
    debounce: function(func, wait, immediate) {
        let timeout;
        return function executedFunction() {
            const context = this;
            const args = arguments;
            
            const later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            
            if (callNow) func.apply(context, args);
        };
    },
    
    /**
     * Throttle function execution
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Component: Execution Status Poller
TestApp.components.ExecutionPoller = {
    active: false,
    interval: null,
    executionIds: new Set(),
    
    start: function(executionIds) {
        if (Array.isArray(executionIds)) {
            executionIds.forEach(id => this.executionIds.add(id));
        } else {
            this.executionIds.add(executionIds);
        }
        
        if (!this.active) {
            this.active = true;
            this.poll();
            this.interval = setInterval(() => this.poll(), TestApp.config.polling_interval);
        }
    },
    
    stop: function() {
        this.active = false;
        this.executionIds.clear();
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    },
    
    poll: function() {
        if (this.executionIds.size === 0) {
            this.stop();
            return;
        }
        
        this.executionIds.forEach(executionId => {
            TestApp.utils.request(`/execute/status/${executionId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.updateExecutionStatus(executionId, data);
                        
                        // Stop polling if execution is complete
                        if (['passed', 'failed', 'error'].includes(data.status)) {
                            this.executionIds.delete(executionId);
                        }
                    }
                })
                .catch(error => {
                    console.warn(`Failed to poll execution ${executionId}:`, error);
                });
        });
    },
    
    updateExecutionStatus: function(executionId, data) {
        // Update status badges
        const statusElements = document.querySelectorAll(`[data-execution-id="${executionId}"] .execution-status`);
        statusElements.forEach(element => {
            element.className = `badge execution-status bg-${this.getStatusColor(data.status)}`;
            element.innerHTML = `<i class="fas ${this.getStatusIcon(data.status)} me-1"></i>${data.status.charAt(0).toUpperCase() + data.status.slice(1)}`;
        });
        
        // Update duration
        const durationElements = document.querySelectorAll(`[data-execution-id="${executionId}"] .execution-duration`);
        durationElements.forEach(element => {
            element.textContent = TestApp.utils.formatDuration(data.duration_seconds);
        });
        
        // Update progress if running
        const progressElements = document.querySelectorAll(`[data-execution-id="${executionId}"] .execution-progress`);
        if (data.status === 'running') {
            progressElements.forEach(element => {
                element.innerHTML = `
                    <div class="progress">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 100%">
                            Running...
                        </div>
                    </div>
                `;
            });
        } else if (data.status !== 'pending') {
            progressElements.forEach(element => {
                element.innerHTML = '';
            });
        }
    },
    
    getStatusColor: function(status) {
        const colors = {
            'pending': 'secondary',
            'running': 'warning',
            'passed': 'success',
            'failed': 'danger',
            'error': 'danger'
        };
        return colors[status] || 'secondary';
    },
    
    getStatusIcon: function(status) {
        const icons = {
            'pending': 'fa-clock',
            'running': 'fa-spinner fa-spin',
            'passed': 'fa-check',
            'failed': 'fa-times',
            'error': 'fa-exclamation-triangle'
        };
        return icons[status] || 'fa-question';
    }
};

// Component: File Upload Handler
TestApp.components.FileUpload = {
    init: function() {
        // Handle drag and drop for upload areas
        document.querySelectorAll('.upload-area').forEach(area => {
            area.addEventListener('dragover', this.handleDragOver);
            area.addEventListener('dragleave', this.handleDragLeave);
            area.addEventListener('drop', this.handleDrop);
        });
    },
    
    handleDragOver: function(e) {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    },
    
    handleDragLeave: function(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');
    },
    
    handleDrop: function(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        const fileInput = e.currentTarget.querySelector('input[type="file"]');
        
        if (fileInput && files.length > 0) {
            fileInput.files = files;
            
            // Trigger change event
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    }
};

// Component: Search and Filter
TestApp.components.SearchFilter = {
    init: function() {
        // Initialize search inputs with debounced handlers
        document.querySelectorAll('[data-search-target]').forEach(input => {
            const target = input.getAttribute('data-search-target');
            const debouncedSearch = TestApp.utils.debounce(
                () => this.performSearch(input, target), 
                300
            );
            
            input.addEventListener('input', debouncedSearch);
        });
        
        // Initialize filter dropdowns
        document.querySelectorAll('[data-filter-target]').forEach(select => {
            const target = select.getAttribute('data-filter-target');
            select.addEventListener('change', () => this.performFilter(select, target));
        });
    },
    
    performSearch: function(input, target) {
        const query = input.value.toLowerCase();
        const targetElements = document.querySelectorAll(target);
        
        targetElements.forEach(element => {
            const searchText = element.textContent.toLowerCase();
            const shouldShow = !query || searchText.includes(query);
            
            element.style.display = shouldShow ? '' : 'none';
        });
        
        this.updateResultCount(target);
    },
    
    performFilter: function(select, target) {
        const filterValue = select.value;
        const filterKey = select.getAttribute('data-filter-key');
        const targetElements = document.querySelectorAll(target);
        
        targetElements.forEach(element => {
            const elementValue = element.getAttribute(`data-${filterKey}`);
            const shouldShow = !filterValue || elementValue === filterValue;
            
            element.style.display = shouldShow ? '' : 'none';
        });
        
        this.updateResultCount(target);
    },
    
    updateResultCount: function(target) {
        const targetElements = document.querySelectorAll(target);
        const visibleCount = Array.from(targetElements).filter(el => el.style.display !== 'none').length;
        
        const countElement = document.querySelector(`[data-result-count="${target}"]`);
        if (countElement) {
            countElement.textContent = `${visibleCount} result${visibleCount !== 1 ? 's' : ''}`;
        }
    }
};

// Component: Form Validation
TestApp.components.FormValidation = {
    init: function() {
        // Add custom validation to forms
        document.querySelectorAll('form[data-validate]').forEach(form => {
            form.addEventListener('submit', this.validateForm.bind(this));
        });
        
        // Real-time validation for specific fields
        document.querySelectorAll('[data-validate-field]').forEach(field => {
            field.addEventListener('blur', this.validateField.bind(this));
        });
    },
    
    validateForm: function(e) {
        const form = e.currentTarget;
        const isValid = this.validateAllFields(form);
        
        if (!isValid) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        form.classList.add('was-validated');
    },
    
    validateAllFields: function(form) {
        const fields = form.querySelectorAll('[data-validate-field]');
        let isValid = true;
        
        fields.forEach(field => {
            if (!this.validateField({ currentTarget: field })) {
                isValid = false;
            }
        });
        
        return isValid;
    },
    
    validateField: function(e) {
        const field = e.currentTarget;
        const validationType = field.getAttribute('data-validate-field');
        const value = field.value;
        
        let isValid = true;
        let message = '';
        
        switch (validationType) {
            case 'email':
                isValid = this.isValidEmail(value);
                message = 'Please enter a valid email address';
                break;
            case 'password':
                isValid = this.isValidPassword(value);
                message = 'Password must be at least 8 characters with uppercase, lowercase, number, and special character';
                break;
            case 'required':
                isValid = value.trim().length > 0;
                message = 'This field is required';
                break;
        }
        
        this.setFieldValidation(field, isValid, message);
        return isValid;
    },
    
    setFieldValidation: function(field, isValid, message) {
        const feedbackElement = field.parentNode.querySelector('.invalid-feedback') || 
                               this.createFeedbackElement(field);
        
        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            feedbackElement.style.display = 'none';
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            feedbackElement.textContent = message;
            feedbackElement.style.display = 'block';
        }
    },
    
    createFeedbackElement: function(field) {
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
        return feedback;
    },
    
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },
    
    isValidPassword: function(password) {
        return password.length >= 8 &&
               /[a-z]/.test(password) &&
               /[A-Z]/.test(password) &&
               /\d/.test(password) &&
               /[!@#$%^&*(),.?":{}|<>]/.test(password);
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    TestApp.init();
    TestApp.components.FileUpload.init();
    TestApp.components.SearchFilter.init();
    TestApp.components.FormValidation.init();
});

// Handle page visibility changes to pause/resume polling
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, reduce polling frequency or pause
        TestApp.components.ExecutionPoller.stop();
    } else {
        // Page is visible, resume normal polling if needed
        const runningExecutions = document.querySelectorAll('[data-execution-status="running"]');
        if (runningExecutions.length > 0) {
            const executionIds = Array.from(runningExecutions).map(el => 
                el.getAttribute('data-execution-id')
            );
            TestApp.components.ExecutionPoller.start(executionIds);
        }
    }
});

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    
    // Show user-friendly error message
    TestApp.utils.showToast(
        'An unexpected error occurred. Please refresh the page if problems persist.',
        'danger'
    );
});

// Handle network errors
window.addEventListener('online', function() {
    TestApp.utils.showToast('Connection restored', 'success');
});

window.addEventListener('offline', function() {
    TestApp.utils.showToast('Connection lost. Some features may not work.', 'warning');
});
