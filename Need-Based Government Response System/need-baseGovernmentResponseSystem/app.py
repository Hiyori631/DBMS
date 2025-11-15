from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import psycopg2
import json
import bcrypt

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# In-memory data storage (loaded from database) 
requests_db = []
users_db = {
    'citizens': {},
    'government': {}
}
audit_logs = []  # Audit trail for system actions
staff_db = []  # Government staff database

# Load requests from database on startup
def init_app():
    """Initialize application by loading data from database"""
    global requests_db
    print("Loading requests from database...")
    requests_db = load_requests_from_db()
    print(f"Loaded {len(requests_db)} requests from database")
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="Need-baseGovernmentResponseSystem", 
            user="postgres",
            password="123"
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error: Unable to connect to the database. Check your credentials.")
        print(e)
        return None

# ============================================
# DATABASE HELPER FUNCTIONS FOR REQUESTS
# ============================================

def load_requests_from_db():
    """Load all requests from database into memory"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT request_id, citizen_name, email, phone, location_address,
                   need_type, severity, people_affected, description,
                   vulnerability_group, special_circumstances, is_student,
                   educational_needs, has_evidence, status, submitted_at,
                   updated_at, completed_at, priority_score, 
                   estimated_response_time, assigned_to
            FROM requests
            ORDER BY submitted_at DESC
        """)
        
        rows = cur.fetchall()
        requests_list = []
        
        for row in rows:
            requests_list.append({
                'id': row[0],
                'citizenName': row[1],
                'email': row[2],
                'phone': row[3],
                'location': row[4],
                'needType': row[5],
                'severity': row[6],
                'peopleAffected': row[7],
                'description': row[8],
                'vulnerabilityGroup': row[9] if row[9] else [],
                'specialCircumstances': row[10],
                'isStudent': row[11],
                'studentInfo': row[12] if row[12] else {},
                'hasEvidence': row[13],
                'status': row[14],
                'submittedAt': row[15].isoformat() if row[15] else None,
                'updatedAt': row[16].isoformat() if row[16] else None,
                'completedAt': row[17].isoformat() if row[17] else None,
                'priorityScore': row[18],
                'estimatedResponse': row[19],
                'assignedTo': row[20]
            })
        
        cur.close()
        conn.close()
        return requests_list
    except Exception as e:
        print(f"Error loading requests from database: {e}")
        if conn:
            conn.close()
        return []

def save_request_to_db(request_data):
    """Save a single request to database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO requests (
                request_id, citizen_name, email, phone, location_address,
                need_type, severity, people_affected, description,
                vulnerability_group, special_circumstances, is_student,
                educational_needs, has_evidence, status, priority_score,
                estimated_response_time, submitted_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            request_data['id'],
            request_data['citizenName'],
            request_data['email'],
            request_data.get('phone'),
            request_data.get('location'),
            request_data['needType'],
            request_data['severity'],
            request_data.get('peopleAffected', 1),
            request_data['description'],
            json.dumps(request_data.get('vulnerabilityGroup', [])),
            request_data.get('specialCircumstances'),
            request_data.get('isStudent', False),
            json.dumps(request_data.get('studentInfo', {})),
            request_data.get('hasEvidence', False),
            request_data.get('status', 'pending'),
            request_data.get('priorityScore', 0),
            request_data.get('estimatedResponse'),
            datetime.now()
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving request to database: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def update_request_status_in_db(request_id, new_status, assigned_to=None):
    """Update request status in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        if new_status == 'completed':
            cur.execute("""
                UPDATE requests 
                SET status = %s, updated_at = %s, completed_at = %s, assigned_to = %s
                WHERE request_id = %s
            """, (new_status, datetime.now(), datetime.now(), assigned_to, request_id))
        else:
            cur.execute("""
                UPDATE requests 
                SET status = %s, updated_at = %s, assigned_to = %s
                WHERE request_id = %s
            """, (new_status, datetime.now(), assigned_to, request_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating request status: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

# ============================================
# PASSWORD HASHING FUNCTIONS (BCRYPT)
# ============================================

def hash_password(password):
    """
    Hash a password using bcrypt
    Args:
        password (str): Plain text password
    Returns:
        str: Hashed password
    """
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password, hashed_password):
    """
    Verify a password against its hash
    Args:
        plain_password (str): Plain text password to verify
        hashed_password (str): Hashed password from database
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

# ============================================
# ROLE-BASED ACCESS CONTROL
# ============================================

def get_allowed_need_types_for_role(role, department):
    """
    Map staff departments to the need types they can view and manage
    
    Args:
        role (str): Staff role (analyst, coordinator, support, officer, manager, admin)
        department (str): Staff department
    
    Returns:
        list: List of allowed need types, or None for full access
    """
    # Department-based mapping
    department_mapping = {
        'Educational Support': ['educational'],  # Education only
        'Emergency Services': ['water', 'other'],  # Emergency Services
        'Financial Assistance': ['financial'],  # Financial Assistance
        'Infrastructure & Housing': ['shelter', 'clothing'],  # Infrastructure & Housing
        'Social Services': ['food', 'medical', 'mental-health'],  # Social Services
        'Relief Operations': ['food'],  # Foods & Nutrition
        'Health and Medical Services': ['medical', 'mental-health']  # Health and Medical Services
    }
    
    # Role-based mapping (fallback if department not found)
    role_mapping = {
        'analyst': ['educational'],  # Education only
        'coordinator': ['water', 'financial', 'other'],  # Emergency Services and Financial Assistance
        'support': ['shelter', 'clothing'],  # Infrastructure & Housing
        'officer': ['food', 'medical', 'mental-health']  # Social Services, Relief Operations, Health and Medical Services
    }
    
    # Managers and admins have full access
    if role in ['manager', 'admin']:
        return None  # None means no filtering - can see all
    
    # Check department first, then fall back to role
    if department in department_mapping:
        return department_mapping[department]
    
    return role_mapping.get(role.lower(), None)


def filter_requests_by_role(requests, role, department):
    """
    Filter requests based on staff role and department
    
    Args:
        requests (list): List of all requests
        role (str): Staff role
        department (str): Staff department
    
    Returns:
        list: Filtered requests that the staff member can access
    """
    allowed_types = get_allowed_need_types_for_role(role, department)
    
    print(f"DEBUG FILTER: Role={role}, Dept={department}, Allowed Types={allowed_types}")
    
    # If allowed_types is None, user has full access
    if allowed_types is None:
        print(f"DEBUG: Full access - returning all {len(requests)} requests")
        return requests
    
    # Filter requests by allowed need types
    filtered = [req for req in requests if req.get('needType') in allowed_types]
    print(f"DEBUG: Filtered {len(filtered)} requests from {len(requests)} total")
    for req in filtered:
        print(f"  - {req.get('id')}: {req.get('needType')}")
    
    return filtered


def calculate_avg_response_time(requests):
    """
    Calculate average response time for completed requests
    
    Args:
        requests (list): List of requests
    
    Returns:
        int: Average response time in hours
    """
    completed = [r for r in requests if r['status'] == 'completed']
    if not completed:
        return 0
    
    # Mock calculation - in production, calculate from timestamp data
    return 24  # 24 hours average


# ============================================
# PRIORITY ALGORITHM
# ============================================

# Priority algorithm
def calculate_priority_score(req):
    """Calculate priority score for a relief request"""
    score = 0
    
    # 1. Severity Score (0-40 points)
    severity_scores = {
        'critical': 40,
        'urgent': 30,
        'moderate': 15,
        'low': 5
    }
    score += severity_scores.get(req['severity'], 0)
    
    # 2. Vulnerability Multiplier (1.0-2.5x)
    vulnerability_weights = {
        'children': 0.4,
        'elderly': 0.3,
        'disabled': 0.4,
        'pregnant': 0.3,
        'student': 0.2,
        'none': 0
    }
    
    vulnerability_bonus = sum(vulnerability_weights.get(group, 0) 
                             for group in req.get('vulnerabilityGroup', []))
    score *= (1 + vulnerability_bonus)
    
    # 3. Number of People Affected (0-20 points)
    people_score = min(req.get('peopleAffected', 1) * 2, 20)
    score += people_score
    
    # 4. Need Type Priority
    need_type_priority = {
        'medical': 10,
        'water': 8,
        'food': 7,
        'shelter': 6,
        'mental-health': 5,
        'educational': 4,
        'clothing': 3,
        'financial': 3,
        'other': 2
    }
    score += need_type_priority.get(req.get('needType'), 0)
    
    # 5. Evidence Bonus (5 points)
    if req.get('hasEvidence', False):
        score += 5
    
    # 6. Special Circumstances (5 points)
    if req.get('specialCircumstances'):
        score += 5
    
    return round(score)

def estimate_response_time(priority_score, queue_position):
    """Estimate response time based on priority and queue position"""
    if priority_score >= 80:
        return 'Within 2 hours'
    elif priority_score >= 60:
        return 'Within 6 hours'
    elif priority_score >= 40:
        return 'Within 24 hours'
    else:
        days = (queue_position // 10) + 1
        return f'Within {days} {"day" if days == 1 else "days"}'

def log_audit_action(action_type, user_email, details, entity_type=None, entity_id=None):
    """Log an audit trail entry"""
    audit_entry = {
        'id': f"AUDIT-{str(len(audit_logs) + 1).zfill(6)}",
        'timestamp': datetime.now().isoformat(),
        'action_type': action_type,  # e.g., 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'STATUS_CHANGE'
        'user_email': user_email,
        'user_role': session.get('user_role', 'unknown'),
        'entity_type': entity_type,  # e.g., 'REQUEST', 'STAFF', 'CITIZEN'
        'entity_id': entity_id,
        'details': details,
        'ip_address': request.remote_addr if request else None
    }
    audit_logs.append(audit_entry)
    return audit_entry

def get_dashboard_stats():
    """Calculate dashboard statistics"""
    total_requests = len(requests_db)
    pending = sum(1 for r in requests_db if r['status'] == 'pending')
    in_progress = sum(1 for r in requests_db if r['status'] == 'in-progress')
    completed = sum(1 for r in requests_db if r['status'] == 'completed')
    critical_requests = sum(1 for r in requests_db if r['severity'] == 'critical')
    student_requests = sum(1 for r in requests_db if r.get('isStudent', False))
    
    # Calculate average response time (mock value)
    avg_response_time = 4.5
    
    return {
        'totalRequests': total_requests,
        'pending': pending,
        'inProgress': in_progress,
        'completed': completed,
        'criticalRequests': critical_requests,
        'studentRequests': student_requests,
        'avgResponseTime': avg_response_time
    }

# Routes
@app.route('/')
def index():
    """Landing page"""
    stats = get_dashboard_stats()
    return render_template('index.html', stats=stats)

@app.route('/about')
def about():
    """About Us page"""
    return render_template('about.html')

@app.route('/contact')
def contact():
    """Contact Us page"""
    return render_template('contact.html')

@app.route('/citizen/login')
def citizen_login():
    """Citizen login page"""
    return render_template('citizen_login.html')

@app.route('/citizen/dashboard')
def citizen_dashboard():
    """Citizen dashboard"""
    if 'user_email' not in session or session.get('user_role') != 'citizen':
        return redirect(url_for('citizen_login'))
    
    user_email = session['user_email']
    user_requests = [r for r in requests_db if r['email'] == user_email]
    
    return render_template('citizen_dashboard.html', 
                         user_name=session.get('user_name', 'Citizen'),
                         user_email=user_email,
                         requests=user_requests)

@app.route('/citizen/submit-request')
def citizen_submit_request():
    """Citizen request submission form"""
    if 'user_email' not in session or session.get('user_role') != 'citizen':
        return redirect(url_for('citizen_login'))
    
    return render_template('citizen_request_form.html',
                         user_email=session.get('user_email'))

@app.route('/government/login')
def government_login():
    """Government login page"""
    return render_template('government_login.html')

@app.route('/government/dashboard')
def government_dashboard():
    """Government dashboard"""
    if 'user_email' not in session or session.get('user_role') != 'government':
        return redirect(url_for('government_login'))
    
    # Get user's role and department
    user_role = session.get('user_position', 'officer')  # Default to officer
    user_department = session.get('user_department', 'Relief Operations')
    
    # Filter requests based on role
    filtered_requests = filter_requests_by_role(
        requests_db, 
        user_role, 
        user_department
    )
    
    # Sort requests by priority
    sorted_requests = sorted(filtered_requests, 
                            key=lambda r: (0 if r['status'] == 'pending' 
                                         else 1 if r['status'] == 'in-progress' 
                                         else 2,
                                         -r['priorityScore']))
    
    # Calculate stats based on filtered requests only
    stats = {
        'totalRequests': len(filtered_requests),
        'pending': len([r for r in filtered_requests if r['status'] == 'pending']),
        'inProgress': len([r for r in filtered_requests if r['status'] == 'in-progress']),
        'completed': len([r for r in filtered_requests if r['status'] == 'completed']),
        'criticalRequests': len([r for r in filtered_requests if r['severity'] == 'critical']),
        'studentRequests': len([r for r in filtered_requests if 'student' in r.get('vulnerabilityGroup', [])]),
        'avgResponseTime': calculate_avg_response_time(filtered_requests)
    }
    
    return render_template('government_dashboard.html',
                         user_name=session.get('user_name', 'Official'),
                         user_department=user_department,
                         user_role=user_role,
                         requests=sorted_requests,
                         stats=stats)

@app.route('/admin/login')
def admin_login():
    """Admin login page"""
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard for staff management and audit tracking"""
    if 'user_email' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    staff_list = []
    recent_audits = []
    total_staff = 0
    active_staff = 0
    total_audits = 0
    
    if conn:
        try:
            cur = conn.cursor()
            
            # Get all staff from database
            cur.execute("""
                SELECT staff_id, full_name, email, phone, official_id, department, 
                       role, employee_id, status, joined_date, requests_handled, 
                       permissions, added_by, added_date
                FROM staff 
                ORDER BY added_date DESC
            """)
            staff_rows = cur.fetchall()
            
            for row in staff_rows:
                staff_list.append({
                    'id': row[0],
                    'fullName': row[1],
                    'email': row[2],
                    'phone': row[3],
                    'officialId': row[4],
                    'department': row[5],
                    'role': row[6],
                    'employeeId': row[7],
                    'status': row[8],
                    'joinedDate': row[9].isoformat() if row[9] else None,
                    'requestsHandled': row[10] or 0,
                    'permissions': row[11] or {},
                    'addedBy': row[12],
                    'addedDate': row[13].strftime('%m/%d/%Y') if row[13] else None
                })
            
            # Get staff counts
            cur.execute("SELECT COUNT(*) FROM staff")
            total_staff = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM staff WHERE status = 'active'")
            active_staff = cur.fetchone()[0]
            
            # Get recent audit logs
            cur.execute("""
                SELECT audit_code, timestamp, action_type, user_email, user_role,
                       entity_type, entity_id, details, ip_address
                FROM audit_logs
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            audit_rows = cur.fetchall()
            
            for row in audit_rows:
                recent_audits.append({
                    'id': row[0],
                    'timestamp': row[1].isoformat() if row[1] else None,
                    'action_type': row[2],
                    'user_email': row[3],
                    'user_role': row[4],
                    'entity_type': row[5],
                    'entity_id': row[6],
                    'details': row[7],
                    'ip_address': row[8]
                })
            
            # Get total audit count
            cur.execute("SELECT COUNT(*) FROM audit_logs")
            total_audits = cur.fetchone()[0]
            
            cur.close()
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            conn.close()
    else:
        # Fallback to in-memory data if database connection fails
        staff_list = staff_db
        total_staff = len(staff_db)
        active_staff = sum(1 for s in staff_db if s.get('status') == 'active')
        recent_audits = sorted(audit_logs, key=lambda x: x['timestamp'], reverse=True)[:10]
        total_audits = len(audit_logs)
    
    # Get statistics
    stats = get_dashboard_stats()
    
    admin_stats = {
        **stats,
        'totalStaff': total_staff,
        'activeStaff': active_staff,
        'totalAudits': total_audits
    }
    
    return render_template('admin_dashboard.html',
                         user_name=session.get('user_name', 'Administrator'),
                         staff_list=staff_list,
                         recent_audits=recent_audits,
                         stats=admin_stats)

# API Routes
@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle login for both citizen, government, and admin users with password verification"""
    data = request.json
    role = data.get('role')  # 'citizen', 'government', or 'admin'
    email = data.get('email')
    password = data.get('password', '')
    name = data.get('name', '')
    department = data.get('department', '')
    
    # For demo purposes, if no password provided, allow login (backward compatibility)
    # In production, you should ALWAYS require password verification
    if password:
        # Verify password based on role
        authenticated = False
        user_data = None
        
        if role == 'citizen':
            # Check citizens in users_db
            if email in users_db.get('citizens', {}):
                stored_hash = users_db['citizens'][email].get('password_hash')
                if stored_hash and verify_password(password, stored_hash):
                    authenticated = True
                    user_data = users_db['citizens'][email]
                    name = user_data.get('name', name)
        
        elif role == 'government':
            # Initialize user_position
            user_position = 'officer'  # Default
            
            # Check government users in database (staff table)
            conn = get_db_connection()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT full_name, department, role, password_hash 
                        FROM staff 
                        WHERE email = %s AND status = 'active'
                    """, (email,))
                    staff_record = cur.fetchone()
                    
                    if staff_record and staff_record[3]:
                        if verify_password(password, staff_record[3]):
                            authenticated = True
                            name = staff_record[0]
                            department = staff_record[1]
                            user_position = staff_record[2] if staff_record[2] else 'officer'  # Get the role from database
                            print(f"DEBUG: Login successful - Name: {name}, Dept: {department}, Role: {user_position}")
                    
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"Database error during login: {e}")
                    if conn:
                        conn.close()
            
            # Fallback to in-memory users_db for backward compatibility
            if not authenticated and email in users_db.get('government', {}):
                stored_hash = users_db['government'][email].get('password_hash')
                if stored_hash and verify_password(password, stored_hash):
                    authenticated = True
                    user_data = users_db['government'][email]
                    name = user_data.get('name', name)
                    department = user_data.get('department', department)
                    user_position = user_data.get('role', 'officer')  # Default role
        
        elif role == 'admin':
            # Check admin users in staff_db or dedicated admin list
            admin_user = next((u for u in staff_db if u.get('email') == email and u.get('role') == 'admin'), None)
            if admin_user:
                stored_hash = admin_user.get('password_hash')
                if stored_hash and verify_password(password, stored_hash):
                    authenticated = True
                    user_data = admin_user
                    name = admin_user.get('name', name)
        
        if not authenticated:
            log_audit_action('LOGIN_FAILED', email, f'Failed login attempt for {role}', 'USER', email)
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
    
    # Set session data
    session['user_email'] = email
    session['user_name'] = name
    session['user_role'] = role
    if role == 'government' or role == 'admin':
        session['user_department'] = department
        session['user_position'] = user_position if 'user_position' in locals() else 'officer'  # Store the position/role
    
    # Log the successful login
    log_audit_action('LOGIN', email, f'{role.capitalize()} user logged in successfully')
    
    return jsonify({'success': True, 'role': role, 'name': name})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Handle logout"""
    user_email = session.get('user_email', 'unknown')
    log_audit_action('LOGOUT', user_email, f'User logged out')
    session.clear()
    return jsonify({'success': True})

# ============================================
# REGISTRATION ENDPOINTS
# ============================================

@app.route('/api/register/citizen', methods=['POST'])
def api_register_citizen():
    """Register a new citizen account with password hashing"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    phone = data.get('phone', '')
    
    # Validate required fields
    if not email or not password or not name:
        return jsonify({'success': False, 'error': 'Email, password, and name are required'}), 400
    
    # Check if user already exists
    if email in users_db.get('citizens', {}):
        return jsonify({'success': False, 'error': 'Email already registered'}), 409
    
    # Hash the password
    password_hash = hash_password(password)
    
    # Create citizen account
    if 'citizens' not in users_db:
        users_db['citizens'] = {}
    
    users_db['citizens'][email] = {
        'email': email,
        'password_hash': password_hash,
        'name': name,
        'phone': phone,
        'created_at': datetime.now().isoformat(),
        'is_active': True
    }
    
    # Log the registration
    log_audit_action('REGISTER', email, f'New citizen account created: {name}', 'CITIZEN', email)
    
    return jsonify({
        'success': True, 
        'message': 'Citizen account created successfully',
        'email': email
    })

@app.route('/api/register/government', methods=['POST'])
def api_register_government():
    """Register a new government user account with password hashing"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    department = data.get('department')
    
    # Validate required fields
    if not email or not password or not name or not department:
        return jsonify({'success': False, 'error': 'Email, password, name, and department are required'}), 400
    
    # Check if user already exists
    if email in users_db.get('government', {}):
        return jsonify({'success': False, 'error': 'Email already registered'}), 409
    
    # Hash the password
    password_hash = hash_password(password)
    
    # Create government account
    if 'government' not in users_db:
        users_db['government'] = {}
    
    users_db['government'][email] = {
        'email': email,
        'password_hash': password_hash,
        'name': name,
        'department': department,
        'created_at': datetime.now().isoformat(),
        'is_active': True
    }
    
    # Log the registration
    log_audit_action('REGISTER', email, f'New government account created: {name} ({department})', 'GOVERNMENT', email)
    
    return jsonify({
        'success': True, 
        'message': 'Government account created successfully',
        'email': email
    })

@app.route('/api/change-password', methods=['POST'])
def api_change_password():
    """Change user password"""
    data = request.json
    email = session.get('user_email')
    role = session.get('user_role')
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not email or not role:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    if not old_password or not new_password:
        return jsonify({'success': False, 'error': 'Old and new passwords are required'}), 400
    
    # Verify old password and update
    user_data = None
    if role == 'citizen' and email in users_db.get('citizens', {}):
        user_data = users_db['citizens'][email]
    elif role == 'government' and email in users_db.get('government', {}):
        user_data = users_db['government'][email]
    
    if not user_data:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Verify old password
    if not verify_password(old_password, user_data.get('password_hash', '')):
        log_audit_action('PASSWORD_CHANGE_FAILED', email, 'Failed password change attempt - incorrect old password')
        return jsonify({'success': False, 'error': 'Incorrect old password'}), 401
    
    # Hash and update new password
    new_password_hash = hash_password(new_password)
    user_data['password_hash'] = new_password_hash
    user_data['password_changed_at'] = datetime.now().isoformat()
    
    # Log the password change
    log_audit_action('PASSWORD_CHANGED', email, f'Password changed successfully', 'USER', email)
    
    return jsonify({'success': True, 'message': 'Password changed successfully'})

# ============================================
# REQUEST ENDPOINTS
# ============================================

@app.route('/api/requests', methods=['GET'])
def api_get_requests():
    """Get all requests or filtered by user email or role-based access"""
    user_email = request.args.get('email')
    
    # Check if this is a government user with role-based access
    if session.get('user_role') == 'government':
        user_position = session.get('user_position', 'officer')
        user_department = session.get('user_department', '')
        
        # Apply role-based filtering
        filtered_requests = filter_requests_by_role(
            requests_db,
            user_position,
            user_department
        )
        
        return jsonify(filtered_requests)
    
    # For citizen users, filter by their email
    if user_email:
        filtered_requests = [r for r in requests_db if r['email'] == user_email]
        return jsonify(filtered_requests)
    
    # For admin users or others, return all requests
    return jsonify(requests_db)

@app.route('/api/requests', methods=['POST'])
def api_submit_request():
    """Submit a new relief request"""
    data = request.json
    
    # Generate request ID
    request_id = f"REQ-{str(len(requests_db) + 1).zfill(6)}"
    
    # Create request object
    new_request = {
        'id': request_id,
        'citizenName': data.get('citizenName'),
        'email': data.get('email'),
        'phone': data.get('phone'),
        'location': data.get('location'),
        'needType': data.get('needType'),
        'severity': data.get('severity'),
        'peopleAffected': data.get('peopleAffected', 1),
        'description': data.get('description'),
        'vulnerabilityGroup': data.get('vulnerabilityGroup', ['none']),
        'specialCircumstances': data.get('specialCircumstances'),
        'isStudent': data.get('isStudent', False),
        'educationalNeeds': data.get('educationalNeeds'),
        'hasEvidence': data.get('hasEvidence', False),
        'status': 'pending',
        'submittedAt': datetime.now().isoformat(),
        'updatedAt': datetime.now().isoformat(),
        'verificationCount': 0,
        'priorityScore': 0
    }
    
    # Calculate priority score
    new_request['priorityScore'] = calculate_priority_score(new_request)
    
    # Add to in-memory database
    requests_db.append(new_request)
    
    # Save to PostgreSQL database
    try:
        save_request_to_db(new_request)
    except Exception as e:
        print(f"Error saving request to database: {e}")
        # Continue with in-memory - don't fail the request
    
    # Sort all requests by priority
    requests_db.sort(key=lambda r: (0 if r['status'] == 'pending' 
                                   else 1 if r['status'] == 'in-progress' 
                                   else 2,
                                   -r['priorityScore']))
    
    # Calculate estimated response time
    queue_position = [r['id'] for r in requests_db if r['status'] == 'pending'].index(request_id) + 1
    new_request['estimatedResponseTime'] = estimate_response_time(
        new_request['priorityScore'], 
        queue_position
    )
    
    # Log audit action
    log_audit_action('CREATE', data.get('email'), 
                    f"New {data.get('needType')} request submitted - {data.get('severity')} severity",
                    'REQUEST', request_id)
    
    return jsonify({'success': True, 'request': new_request})

@app.route('/api/requests/<request_id>/status', methods=['PUT'])
def api_update_status(request_id):
    """Update request status - with role-based access control"""
    data = request.json
    new_status = data.get('status')
    
    # Find the request
    for req in requests_db:
        if req['id'] == request_id:
            # Check if user has permission to update this request
            if session.get('user_role') == 'government':
                user_position = session.get('user_position', 'officer')
                user_department = session.get('user_department', '')
                
                # Get allowed need types for this role
                allowed_types = get_allowed_need_types_for_role(user_position, user_department)
                
                # If user has restricted access, check if they can access this request
                if allowed_types is not None and req.get('needType') not in allowed_types:
                    return jsonify({
                        'success': False, 
                        'error': 'You do not have permission to update this request type'
                    }), 403
            
            # Update the request in memory
            old_status = req['status']
            req['status'] = new_status
            req['updatedAt'] = datetime.now().isoformat()
            
            if new_status == 'in-progress' and 'assignedTo' not in req:
                req['assignedTo'] = session.get('user_name', 'Relief Team')
            
            if new_status == 'completed':
                req['completedAt'] = datetime.now().isoformat()
            
            # Update in PostgreSQL database
            try:
                update_request_status_in_db(
                    request_id, 
                    new_status, 
                    req.get('assignedTo')
                )
            except Exception as e:
                print(f"Error updating request status in database: {e}")
                # Continue with in-memory update - don't fail the request
            
            # Log status change
            user_email = session.get('user_email', 'system')
            log_audit_action('STATUS_CHANGE', user_email,
                           f"Request {request_id} status changed from {old_status} to {new_status}",
                           'REQUEST', request_id)
            
            return jsonify({'success': True, 'request': req})
    
    return jsonify({'success': False, 'error': 'Request not found'}), 404

@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    """Get dashboard statistics"""
    return jsonify(get_dashboard_stats())

# ============================================
# ADMIN API ROUTES - Staff Management
# ============================================

@app.route('/api/admin/staff', methods=['GET'])
def api_get_staff():
    """Get all government staff members from database"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify(staff_db)  # Fallback to in-memory
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT staff_id, full_name, email, phone, official_id, department, 
                   role, employee_id, status, joined_date, requests_handled, permissions
            FROM staff 
            ORDER BY added_date DESC
        """)
        staff_rows = cur.fetchall()
        
        staff_list = []
        for row in staff_rows:
            staff_list.append({
                'id': row[0],
                'fullName': row[1],
                'email': row[2],
                'phone': row[3],
                'officialId': row[4],
                'department': row[5],
                'role': row[6],
                'employeeId': row[7],
                'status': row[8],
                'joinedDate': row[9].isoformat() if row[9] else None,
                'requestsHandled': row[10] or 0,
                'permissions': row[11] or {}
            })
        
        cur.close()
        conn.close()
        return jsonify(staff_list)
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.close()
        return jsonify(staff_db)  # Fallback

@app.route('/api/admin/staff', methods=['POST'])
def api_create_staff():
    """Create a new staff member in database"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    conn = get_db_connection()
    
    if not conn:
        # Fallback to in-memory
        staff_id = f"STAFF-{str(len(staff_db) + 1).zfill(4)}"
        
        # Hash password if provided
        password_hash = None
        if 'password' in data and data['password']:
            password_hash = hash_password(data['password'])
        
        new_staff = {
            'id': staff_id,
            'fullName': data.get('fullName'),
            'email': data.get('email'),
            'password': password_hash,  # Store hashed password
            'phone': data.get('phone'),
            'department': data.get('department'),
            'role': data.get('role', 'officer'),
            'employeeId': data.get('employeeId'),
            'status': 'active',
            'joinedDate': datetime.now().isoformat(),
            'lastLogin': None,
            'requestsHandled': 0,
            'permissions': data.get('permissions', {})
        }
        staff_db.append(new_staff)
        return jsonify({'success': True, 'staff': new_staff})
    
    try:
        cur = conn.cursor()
        
        # Generate staff ID
        cur.execute("SELECT COUNT(*) FROM staff")
        count = cur.fetchone()[0]
        staff_id = f"STAFF-{str(count + 1).zfill(4)}"
        
        # Hash password if provided
        password_hash = None
        if 'password' in data and data['password']:
            password_hash = hash_password(data['password'])
        
        # Insert staff member
        cur.execute("""
            INSERT INTO staff (staff_id, full_name, email, password_hash, phone, official_id, department, 
                               role, employee_id, status, permissions, added_by, added_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING staff_id, full_name, email, phone, official_id, department, role, 
                      employee_id, status, joined_date, requests_handled, permissions
        """, (
            staff_id,
            data.get('fullName'),
            data.get('email'),
            password_hash,
            data.get('phone'),
            data.get('employeeId'),  # Use employeeId as official_id
            data.get('department'),
            data.get('role', 'officer'),
            data.get('employeeId'),
            'active',
            json.dumps(data.get('permissions', {})),
            session.get('user_email', 'system')
        ))
        
        row = cur.fetchone()
        new_staff = {
            'id': row[0],
            'fullName': row[1],
            'email': row[2],
            'phone': row[3],
            'officialId': row[4],
            'department': row[5],
            'role': row[6],
            'employeeId': row[7],
            'status': row[8],
            'joinedDate': row[9].isoformat() if row[9] else None,
            'requestsHandled': row[10] or 0,
            'permissions': row[11] or {}
        }
        
        # Log audit action in database
        admin_email = session.get('user_email', 'system')
        cur.execute("""
            INSERT INTO audit_logs (audit_code, action_type, user_email, user_role, 
                                    entity_type, entity_id, details, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'CREATE',
            admin_email,
            'admin',
            'STAFF',
            staff_id,
            f"New staff member created: {new_staff['fullName']} ({new_staff['email']}) - {new_staff['role']}",
            request.remote_addr
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'staff': new_staff})
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/staff/<staff_id>', methods=['PUT'])
def api_update_staff(staff_id):
    """Update staff member details in database"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    conn = get_db_connection()
    
    if not conn:
        # Fallback to in-memory
        for staff in staff_db:
            if staff['id'] == staff_id:
                if 'fullName' in data:
                    staff['fullName'] = data['fullName']
                if 'email' in data:
                    staff['email'] = data['email']
                if 'phone' in data:
                    staff['phone'] = data['phone']
                if 'department' in data:
                    staff['department'] = data['department']
                if 'role' in data:
                    staff['role'] = data['role']
                if 'status' in data:
                    staff['status'] = data['status']
                if 'permissions' in data:
                    staff['permissions'] = data['permissions']
                return jsonify({'success': True, 'staff': staff})
        return jsonify({'success': False, 'error': 'Staff not found'}), 404
    
    try:
        cur = conn.cursor()
        
        # Build UPDATE query dynamically
        update_fields = []
        params = []
        
        if 'fullName' in data:
            update_fields.append("full_name = %s")
            params.append(data['fullName'])
        if 'email' in data:
            update_fields.append("email = %s")
            params.append(data['email'])
        if 'phone' in data:
            update_fields.append("phone = %s")
            params.append(data['phone'])
        if 'department' in data:
            update_fields.append("department = %s")
            params.append(data['department'])
        if 'role' in data:
            update_fields.append("role = %s")
            params.append(data['role'])
        if 'status' in data:
            update_fields.append("status = %s")
            params.append(data['status'])
        if 'permissions' in data:
            update_fields.append("permissions = %s")
            params.append(json.dumps(data['permissions']))
        
        if not update_fields:
            return jsonify({'success': False, 'error': 'No fields to update'}), 400
        
        params.append(staff_id)
        query = f"UPDATE staff SET {', '.join(update_fields)} WHERE staff_id = %s RETURNING staff_id, full_name, email, phone, official_id, department, role, employee_id, status"
        
        cur.execute(query, params)
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Staff not found'}), 404
        
        updated_staff = {
            'id': row[0],
            'fullName': row[1],
            'email': row[2],
            'phone': row[3],
            'officialId': row[4],
            'department': row[5],
            'role': row[6],
            'employeeId': row[7],
            'status': row[8]
        }
        
        # Log audit action
        admin_email = session.get('user_email', 'system')
        cur.execute("""
            INSERT INTO audit_logs (audit_code, action_type, user_email, user_role, 
                                    entity_type, entity_id, details, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'UPDATE',
            admin_email,
            'admin',
            'STAFF',
            staff_id,
            f"Staff {staff_id} updated",
            request.remote_addr
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'staff': updated_staff})
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/staff/<staff_id>', methods=['DELETE'])
def api_delete_staff(staff_id):
    """Delete/deactivate staff member in database"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    
    if not conn:
        # Fallback to in-memory
        for i, staff in enumerate(staff_db):
            if staff['id'] == staff_id:
                staff['status'] = 'inactive'
                staff['deactivatedDate'] = datetime.now().isoformat()
                return jsonify({'success': True, 'message': 'Staff deactivated'})
        return jsonify({'success': False, 'error': 'Staff not found'}), 404
    
    try:
        cur = conn.cursor()
        
        # Soft delete - mark as inactive and set deactivated date
        cur.execute("""
            UPDATE staff 
            SET status = 'inactive', deactivated_date = CURRENT_TIMESTAMP
            WHERE staff_id = %s
            RETURNING full_name, email
        """, (staff_id,))
        
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Staff not found'}), 404
        
        # Log audit action
        admin_email = session.get('user_email', 'system')
        cur.execute("""
            INSERT INTO audit_logs (audit_code, action_type, user_email, user_role, 
                                    entity_type, entity_id, details, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'DELETE',
            admin_email,
            'admin',
            'STAFF',
            staff_id,
            f"Staff member deactivated: {row[0]} ({row[1]})",
            request.remote_addr
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Staff deactivated'})
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# ADMIN API ROUTES - Audit Tracking
# ============================================

@app.route('/api/admin/audit-logs', methods=['GET'])
def api_get_audit_logs():
    """Get audit logs with optional filtering from database"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get query parameters
    action_type = request.args.get('action_type')
    user_email = request.args.get('user_email')
    entity_type = request.args.get('entity_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 100))
    
    conn = get_db_connection()
    
    if not conn:
        # Fallback to in-memory
        filtered_logs = audit_logs
        if action_type:
            filtered_logs = [log for log in filtered_logs if log['action_type'] == action_type]
        sorted_logs = sorted(filtered_logs, key=lambda x: x['timestamp'], reverse=True)[:limit]
        return jsonify({'success': True, 'logs': sorted_logs, 'total': len(filtered_logs), 'returned': len(sorted_logs)})
    
    try:
        cur = conn.cursor()
        
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if action_type:
            where_clauses.append("action_type = %s")
            params.append(action_type)
        if user_email:
            where_clauses.append("user_email = %s")
            params.append(user_email)
        if entity_type:
            where_clauses.append("entity_type = %s")
            params.append(entity_type)
        if start_date:
            where_clauses.append("timestamp >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("timestamp <= %s")
            params.append(end_date)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        params.append(limit)
        
        query = f"""
            SELECT audit_code, timestamp, action_type, user_email, user_role,
                   entity_type, entity_id, details, ip_address
            FROM audit_logs
            WHERE {where_sql}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'timestamp': row[1].isoformat() if row[1] else None,
                'action_type': row[2],
                'user_email': row[3],
                'user_role': row[4],
                'entity_type': row[5],
                'entity_id': row[6],
                'details': row[7],
                'ip_address': row[8]
            })
        
        # Get total count
        cur.execute(f"SELECT COUNT(*) FROM audit_logs WHERE {where_sql}", params[:-1])
        total = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': total,
            'returned': len(logs)
        })
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/audit-stats', methods=['GET'])
def api_get_audit_stats():
    """Get audit statistics"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    total_actions = len(audit_logs)
    
    # Count by action type
    action_counts = {}
    for log in audit_logs:
        action_type = log['action_type']
        action_counts[action_type] = action_counts.get(action_type, 0) + 1
    
    # Count by user
    user_activity = {}
    for log in audit_logs:
        user = log['user_email']
        user_activity[user] = user_activity.get(user, 0) + 1
    
    # Most active users (top 5)
    top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Recent activity (last 24 hours - mock)
    recent_count = sum(1 for log in audit_logs[-100:])
    
    return jsonify({
        'success': True,
        'stats': {
            'totalActions': total_actions,
            'actionCounts': action_counts,
            'topUsers': [{'email': email, 'count': count} for email, count in top_users],
            'recentActivity': recent_count
        }
    })

@app.route('/api/admin/system-stats', methods=['GET'])
def api_get_system_stats():
    """Get comprehensive system statistics for admin"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    base_stats = get_dashboard_stats()
    
    # Staff statistics
    total_staff = len(staff_db)
    active_staff = sum(1 for s in staff_db if s.get('status') == 'active')
    staff_by_department = {}
    for staff in staff_db:
        dept = staff.get('department', 'Unknown')
        staff_by_department[dept] = staff_by_department.get(dept, 0) + 1
    
    # Request statistics by status over time (mock data)
    request_trends = {
        'pending_trend': [12, 15, 18, 14, 10],
        'in_progress_trend': [3, 5, 7, 6, 4],
        'completed_trend': [5, 8, 10, 15, 20]
    }
    
    return jsonify({
        'success': True,
        'stats': {
            **base_stats,
            'totalStaff': total_staff,
            'activeStaff': active_staff,
            'inactiveStaff': total_staff - active_staff,
            'staffByDepartment': staff_by_department,
            'totalAuditLogs': len(audit_logs),
            'requestTrends': request_trends
        }
    })

# Initialize with some mock data
def init_mock_data():
    """Initialize with sample requests, staff, and test users with hashed passwords"""
    
    # Initialize test users with bcrypt hashed passwords
    # Password for all test accounts: "password123"
    test_password_hash = hash_password("password123")
    
    # Initialize citizens
    if 'citizens' not in users_db:
        users_db['citizens'] = {}
    
    if len(users_db['citizens']) == 0:
        users_db['citizens']['john@example.com'] = {
            'email': 'john@example.com',
            'password_hash': test_password_hash,
            'name': 'John Doe',
            'phone': '+1-555-0001',
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
        users_db['citizens']['sarah@example.com'] = {
            'email': 'sarah@example.com',
            'password_hash': test_password_hash,
            'name': 'Sarah Smith',
            'phone': '+1-555-0002',
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
    
    # Initialize government users
    if 'government' not in users_db:
        users_db['government'] = {}
    
    if len(users_db['government']) == 0:
        users_db['government']['michael.chen@gov.example'] = {
            'email': 'michael.chen@gov.example',
            'password_hash': test_password_hash,
            'name': 'Michael Chen',
            'department': 'Relief Operations',
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
        users_db['government']['emily.rodriguez@gov.example'] = {
            'email': 'emily.rodriguez@gov.example',
            'password_hash': test_password_hash,
            'name': 'Emily Rodriguez',
            'department': 'Medical Services',
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
    
    # Initialize sample requests
    if len(requests_db) == 0:
        sample_requests = [
            {
                'id': 'REQ-000001',
                'citizenName': 'John Doe',
                'email': 'john@example.com',
                'phone': '+1-555-0001',
                'location': {
                    'address': '123 Main St, Downtown District',
                    'coordinates': {'lat': 40.7128, 'lng': -74.0060}
                },
                'needType': 'medical',
                'severity': 'critical',
                'peopleAffected': 3,
                'description': 'Urgent medical supplies needed for elderly parent',
                'vulnerabilityGroup': ['elderly', 'disabled'],
                'specialCircumstances': 'Chronic illness, mobility limited',
                'isStudent': False,
                'hasEvidence': True,
                'status': 'in-progress',
                'submittedAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat(),
                'verificationCount': 2,
                'priorityScore': 95,
                'estimatedResponseTime': 'Within 2 hours',
                'assignedTo': 'Relief Team 1'
            },
            {
                'id': 'REQ-000002',
                'citizenName': 'Sarah Smith',
                'email': 'sarah@example.com',
                'phone': '+1-555-0002',
                'location': {
                    'address': '456 Oak Ave, West District',
                    'coordinates': {'lat': 40.7228, 'lng': -74.0160}
                },
                'needType': 'educational',
                'severity': 'urgent',
                'peopleAffected': 1,
                'description': 'Need laptop for online classes, exam next week',
                'vulnerabilityGroup': ['student'],
                'specialCircumstances': '',
                'isStudent': True,
                'educationalNeeds': {
                    'type': 'devices',
                    'details': 'Engineering student, need computer for CAD software'
                },
                'hasEvidence': False,
                'status': 'pending',
                'submittedAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat(),
                'verificationCount': 0,
                'priorityScore': 68,
                'estimatedResponseTime': 'Within 6 hours'
            }
        ]
        requests_db.extend(sample_requests)
    
    # Initialize sample staff data with hashed passwords (COMMENTED OUT - Use database instead)
    # if len(staff_db) == 0:
    #     sample_staff = [
    #         {
    #             'id': 'ADMIN-0001',
    #             'fullName': 'Admin User',
    #             'name': 'Admin User',
    #             'email': 'admin@gov.example',
    #             'password_hash': test_password_hash,
    #             'phone': '+1-555-9999',
    #             'department': 'Administration',
    #             'role': 'admin',
    #             'employeeId': 'ADMIN-001',
    #             'status': 'active',
    #             'joinedDate': '2020-01-01T08:00:00',
    #             'lastLogin': datetime.now().isoformat(),
    #             'requestsHandled': 0,
    #             'permissions': ['all']
    #         },
    #         {
    #             'id': 'STAFF-0001',
    #             'fullName': 'Michael Chen',
    #             'name': 'Michael Chen',
    #             'email': 'michael.chen@gov.example',
    #             'password_hash': test_password_hash,
    #             'phone': '+1-555-1001',
    #             'department': 'Relief Operations',
    #             'role': 'manager',
    #             'employeeId': 'EMP-2021-001',
    #             'status': 'active',
    #             'joinedDate': '2021-03-15T08:00:00',
    #             'lastLogin': datetime.now().isoformat(),
    #             'requestsHandled': 142,
    #             'permissions': ['view_requests', 'update_status', 'assign_teams', 'view_reports']
    #         },
    #         {
    #             'id': 'STAFF-0002',
    #             'fullName': 'Emily Rodriguez',
    #             'name': 'Emily Rodriguez',
    #             'email': 'emily.rodriguez@gov.example',
    #             'password_hash': test_password_hash,
    #             'phone': '+1-555-1002',
    #             'department': 'Medical Services',
    #             'role': 'officer',
    #             'employeeId': 'EMP-2022-015',
    #             'status': 'active',
    #             'joinedDate': '2022-06-20T08:00:00',
    #             'lastLogin': datetime.now().isoformat(),
    #             'requestsHandled': 87,
    #             'permissions': ['view_requests', 'update_status']
    #         },
    #         {
    #             'id': 'STAFF-0003',
    #             'fullName': 'David Kumar',
    #             'name': 'David Kumar',
    #             'email': 'david.kumar@gov.example',
    #             'password_hash': test_password_hash,
    #             'phone': '+1-555-1003',
    #             'department': 'Educational Support',
    #             'role': 'officer',
    #             'employeeId': 'EMP-2022-028',
    #             'status': 'active',
    #             'joinedDate': '2022-08-10T08:00:00',
    #             'lastLogin': datetime.now().isoformat(),
    #             'requestsHandled': 63,
    #             'permissions': ['view_requests', 'update_status']
    #         },
    #         {
    #             'id': 'STAFF-0004',
    #             'fullName': 'Sarah Johnson',
    #             'email': 'sarah.johnson@gov.example',
    #             'phone': '+1-555-1004',
    #             'department': 'Relief Operations',
    #             'role': 'officer',
    #             'employeeId': 'EMP-2023-007',
    #             'status': 'active',
    #             'joinedDate': '2023-02-01T08:00:00',
    #             'lastLogin': datetime.now().isoformat(),
    #             'requestsHandled': 45,
    #             'permissions': ['view_requests', 'update_status']
    #         }
    #     ]
    #     staff_db.extend(sample_staff)
    
    # Initialize sample audit logs
    if len(audit_logs) == 0:
        sample_audits = [
            {
                'id': 'AUDIT-000001',
                'timestamp': datetime.now().isoformat(),
                'action_type': 'LOGIN',
                'user_email': 'michael.chen@gov.example',
                'user_role': 'government',
                'entity_type': None,
                'entity_id': None,
                'details': 'Government user logged in',
                'ip_address': '192.168.1.100'
            },
            {
                'id': 'AUDIT-000002',
                'timestamp': datetime.now().isoformat(),
                'action_type': 'STATUS_CHANGE',
                'user_email': 'michael.chen@gov.example',
                'user_role': 'government',
                'entity_type': 'REQUEST',
                'entity_id': 'REQ-000001',
                'details': 'Request REQ-000001 status changed from pending to in-progress',
                'ip_address': '192.168.1.100'
            }
        ]
        audit_logs.extend(sample_audits)

if __name__ == '__main__':
    # Load requests from database on startup
    init_app()
    
    # Initialize mock data for testing (if needed)
    init_mock_data()
    
    # Start the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)
