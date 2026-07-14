document.addEventListener('DOMContentLoaded', () => {
    // --- UI Elements ---
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const showRegisterBtn = document.getElementById('show-register');
    const showLoginBtn = document.getElementById('show-login');
    const authView = document.getElementById('auth-view');
    const dashboardView = document.getElementById('dashboard-view');
    const userGreeting = document.getElementById('user-greeting');
    const logoutBtn = document.getElementById('logout-btn');

    // Role-specific dashboards
    const adminDash = document.getElementById('admin-dashboard');
    const teacherDash = document.getElementById('teacher-dashboard');
    const studentDash = document.getElementById('student-dashboard');

    // Register Form specific
    const regRoleSelect = document.getElementById('reg-role');
    const regFaceGroup = document.getElementById('reg-face-group');
    const regFaceInput = document.getElementById('reg-face');

    // --- State ---
    let currentUser = null;

    // --- Toast Notifications ---
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease-out forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // --- View Switching ---
    function showView(viewId) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(viewId).classList.add('active');
    }

    showRegisterBtn.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    });

    showLoginBtn.addEventListener('click', (e) => {
        e.preventDefault();
        registerForm.style.display = 'none';
        loginForm.style.display = 'block';
    });

    // Toggle face photo requirement based on role
    regRoleSelect.addEventListener('change', (e) => {
        if (e.target.value === 'student') {
            regFaceGroup.style.display = 'block';
            regFaceInput.required = true;
        } else {
            regFaceGroup.style.display = 'none';
            regFaceInput.required = false;
        }
    });

    // --- Auth Logic ---

    // Check if already logged in
    async function checkSession() {
        try {
            const res = await fetch('/api/me');
            if (res.ok) {
                currentUser = await res.json();
                loadDashboard();
            } else {
                showView('auth-view');
            }
        } catch (err) {
            showView('auth-view');
        }
    }

    // Login
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            
            if (res.ok) {
                currentUser = data;
                showToast('Login successful!');
                loginForm.reset();
                loadDashboard();
            } else {
                showToast(data.error || 'Login failed', 'error');
            }
        } catch (err) {
            showToast('Network error', 'error');
        }
    });

    // Register
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Use FormData for multipart upload
        const formData = new FormData();
        formData.append('name', document.getElementById('reg-name').value);
        formData.append('username', document.getElementById('reg-username').value);
        formData.append('password', document.getElementById('reg-password').value);
        const role = document.getElementById('reg-role').value;
        formData.append('role', role);

        if (role === 'student') {
            const faceFile = regFaceInput.files[0];
            if (!faceFile) {
                showToast('Face photo is required for students', 'error');
                return;
            }
            formData.append('face_image', faceFile);
        }

        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                // Don't set Content-Type, browser will set it to multipart/form-data with boundary automatically
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                showToast('Registration successful! Please login.');
                registerForm.reset();
                showLoginBtn.click(); // Switch back to login
            } else {
                showToast(data.error || 'Registration failed', 'error');
            }
        } catch (err) {
            showToast('Network error', 'error');
        }
    });

    // Logout
    logoutBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/logout', { method: 'POST' });
            currentUser = null;
            showView('auth-view');
            showToast('Logged out successfully');
        } catch (err) {
            showToast('Logout failed', 'error');
        }
    });

    // --- Dashboard Logic ---
    async function loadDashboard() {
        if (!currentUser) return;
        
        userGreeting.textContent = `Welcome, ${currentUser.name}!`;
        showView('dashboard-view');
        
        // Hide all specific dashboards first
        adminDash.style.display = 'none';
        teacherDash.style.display = 'none';
        studentDash.style.display = 'none';

        try {
            const res = await fetch('/api/dashboard');
            if (res.ok) {
                const data = await res.json();
                
                if (currentUser.role === 'admin') {
                    adminDash.style.display = 'block';
                    renderStats('admin-stats', data);
                } else if (currentUser.role === 'teacher') {
                    teacherDash.style.display = 'block';
                    renderStats('teacher-stats', data);
                } else if (currentUser.role === 'student') {
                    studentDash.style.display = 'block';
                    loadStudentAttendance();
                }
            }
        } catch (err) {
            console.error('Failed to load dashboard data', err);
        }
    }

    function renderStats(containerId, data) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        
        const labels = {
            total_users: 'Total Users',
            total_classes: 'Total Classes',
            total_lectures: 'Total Lectures',
            active_sessions: 'Active Sessions'
        };

        for (const [key, value] of Object.entries(data)) {
            if (labels[key]) {
                container.innerHTML += `
                    <div class="stat-card">
                        <h4>${labels[key]}</h4>
                        <div class="stat-value">${value}</div>
                    </div>
                `;
            }
        }
    }

    async function loadStudentAttendance() {
        try {
            const res = await fetch('/api/my-attendance');
            if (res.ok) {
                const data = await res.json();
                const container = document.getElementById('student-stats');
                container.innerHTML = `
                    <div class="stat-card">
                        <h4>Total Present</h4>
                        <div class="stat-value">${data.total_present || 0}</div>
                    </div>
                `;
            }
        } catch (err) {
            console.error('Failed to load student attendance', err);
        }
    }

    // Initialize
    checkSession();
});
