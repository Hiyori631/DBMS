-- ============================================
-- NEED-BASED GOVERNMENT RESPONSE SYSTEM
-- PostgreSQL Database Schema
-- ============================================

-- Drop existing tables (if needed for fresh start)
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS requests CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS citizens CASCADE;

-- ============================================
-- CITIZENS TABLE
-- ============================================
CREATE TABLE citizens (
    citizen_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- STAFF TABLE (Government Staff & Admins)
-- ============================================
CREATE TABLE staff (
    staff_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    phone VARCHAR(50),
    official_id VARCHAR(50) UNIQUE,
    department VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'manager', 'officer', 'coordinator', 'analyst')),
    employee_id VARCHAR(50) UNIQUE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'on-leave')),
    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    requests_handled INTEGER DEFAULT 0,
    permissions JSONB,
    added_by VARCHAR(255),
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deactivated_date TIMESTAMP
);

-- ============================================
-- REQUESTS TABLE (Relief/Assistance Requests)
-- ============================================
CREATE TABLE requests (
    request_id VARCHAR(50) PRIMARY KEY,
    citizen_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    location_address TEXT,
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    need_type VARCHAR(50) NOT NULL CHECK (need_type IN ('medical', 'water', 'food', 'shelter', 'mental-health', 'educational', 'clothing', 'financial', 'other')),
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('critical', 'urgent', 'moderate', 'low')),
    people_affected INTEGER DEFAULT 1,
    description TEXT NOT NULL,
    vulnerability_group JSONB,
    special_circumstances TEXT,
    is_student BOOLEAN DEFAULT FALSE,
    educational_needs JSONB,
    has_evidence BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in-progress', 'completed', 'rejected', 'cancelled')),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    verification_count INTEGER DEFAULT 0,
    priority_score INTEGER DEFAULT 0,
    estimated_response_time VARCHAR(100),
    assigned_to VARCHAR(100),
    assigned_staff_id VARCHAR(50),
    FOREIGN KEY (assigned_staff_id) REFERENCES staff(staff_id) ON DELETE SET NULL
);

-- ============================================
-- AUDIT LOGS TABLE (System Activity Tracking)
-- ============================================
CREATE TABLE audit_logs (
    audit_id SERIAL PRIMARY KEY,
    audit_code VARCHAR(50) UNIQUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN ('LOGIN', 'LOGOUT', 'CREATE', 'UPDATE', 'DELETE', 'STATUS_CHANGE', 'REGISTER', 'PASSWORD_CHANGED', 'LOGIN_FAILED', 'PASSWORD_CHANGE_FAILED')),
    user_email VARCHAR(255) NOT NULL,
    user_role VARCHAR(50),
    entity_type VARCHAR(50),
    entity_id VARCHAR(50),
    details TEXT,
    ip_address VARCHAR(50)
);

-- ============================================
-- INDEXES for Performance
-- ============================================

-- Citizens indexes
CREATE INDEX idx_citizens_email ON citizens(email);
CREATE INDEX idx_citizens_active ON citizens(is_active);

-- Staff indexes
CREATE INDEX idx_staff_email ON staff(email);
CREATE INDEX idx_staff_department ON staff(department);
CREATE INDEX idx_staff_role ON staff(role);
CREATE INDEX idx_staff_status ON staff(status);
CREATE INDEX idx_staff_official_id ON staff(official_id);

-- Requests indexes
CREATE INDEX idx_requests_email ON requests(email);
CREATE INDEX idx_requests_status ON requests(status);
CREATE INDEX idx_requests_severity ON requests(severity);
CREATE INDEX idx_requests_priority ON requests(priority_score DESC);
CREATE INDEX idx_requests_submitted ON requests(submitted_at DESC);
CREATE INDEX idx_requests_assigned_staff ON requests(assigned_staff_id);

-- Audit logs indexes
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_logs(user_email);
CREATE INDEX idx_audit_action_type ON audit_logs(action_type);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);

-- ============================================
-- SAMPLE DATA
-- ============================================

-- Insert sample citizens - password: "password123"
INSERT INTO citizens (email, password_hash, full_name, phone) VALUES
('john@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYNJL6BQMKG', 'John Doe', '+1-555-0001'),
('sarah@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYNJL6BQMKG', 'Sarah Smith', '+1-555-0002'),
('maria@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYNJL6BQMKG', 'Maria Garcia', '+1-555-0003');

-- Insert sample staff (including admin) - password: "password123"
INSERT INTO staff (staff_id, full_name, email, password_hash, phone, official_id, department, role, employee_id, status, joined_date, requests_handled, permissions, added_by, added_date) VALUES
('ADMIN-0001', 'John Administrator', 'john.administrator@gov.example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYNJL6BQMKG', '+1-555-7716', 'GOV-10001', 'Administration', 'admin', 'GOV-10001', 'active', '2020-01-01 08:00:00', 0, '{"viewRequests": true, "manageRequests": true, "assignRequests": true, "viewAnalytics": true, "manageStaff": true, "viewAuditLogs": true, "systemSettings": true}', 'admin@gov.example.com', '2025-09-05 10:00:00'),
('STAFF-0001', 'Sarah Mitchell', 'sarah.mitchell@gov.example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYNJL6BQMKG', '+1-555-9616', 'GOV-10002', 'Social Services', 'officer', 'GOV-10002', 'active', '2022-06-20 08:00:00', 87, '{"viewRequests": true, "manageRequests": true}', 'admin@gov.example.com', '2025-07-13 09:30:00'),
('STAFF-0002', 'David Chen', 'david.chen@gov.example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYNJL6BQMKG', '+1-555-0540', 'GOV-10003', 'Emergency Services', 'coordinator', 'GOV-10003', 'active', '2022-08-10 08:00:00', 63, '{"viewRequests": true, "manageRequests": true, "assignRequests": true}', 'admin@gov.example.com', '2025-08-27 14:15:00'),
('STAFF-0003', 'Maria Garcia', 'maria.garcia@gov.example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYNJL6BQMKG', '+1-555-4154', 'GOV-10004', 'Health & Medical', 'officer', 'GOV-10004', 'active', '2023-02-01 08:00:00', 45, '{"viewRequests": true, "manageRequests": true}', 'admin@gov.example.com', '2025-10-07 11:20:00'),
('STAFF-0004', 'Robert Taylor', 'robert.taylor@gov.example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYNJL6BQMKG', '+1-555-4972', 'GOV-10005', 'Education Services', 'analyst', 'GOV-10005', 'on-leave', '2021-03-15 08:00:00', 142, '{"viewRequests": true, "viewAnalytics": true}', 'admin@gov.example.com', '2025-07-19 16:45:00');

-- Insert sample requests
INSERT INTO requests (request_id, citizen_name, email, phone, location_address, location_lat, location_lng, need_type, severity, people_affected, description, vulnerability_group, special_circumstances, is_student, educational_needs, has_evidence, status, submitted_at, priority_score, estimated_response_time, assigned_to, assigned_staff_id) VALUES
('REQ-000001', 'John Doe', 'john@example.com', '+1-555-0001', '123 Main St, Downtown District', 40.7128, -74.0060, 'medical', 'critical', 3, 'Urgent medical supplies needed for elderly parent', '["elderly", "disabled"]', 'Chronic illness, mobility limited', FALSE, NULL, TRUE, 'in-progress', CURRENT_TIMESTAMP - INTERVAL '2 hours', 95, 'Within 2 hours', 'Relief Team 1', 'STAFF-0001'),
('REQ-000002', 'Sarah Smith', 'sarah@example.com', '+1-555-0002', '456 Oak Ave, West District', 40.7228, -74.0160, 'educational', 'urgent', 1, 'Need laptop for online classes, exam next week', '["student"]', '', TRUE, '{"type": "devices", "details": "Engineering student, need computer for CAD software"}', FALSE, 'pending', CURRENT_TIMESTAMP - INTERVAL '1 hour', 68, 'Within 6 hours', NULL, NULL),
('REQ-000003', 'Maria Garcia', 'maria@example.com', '+1-555-0003', '789 Pine Rd, East District', 40.7328, -74.0260, 'food', 'urgent', 5, 'Family needs food assistance, lost job recently', '["children"]', 'Single parent with 3 children', FALSE, NULL, TRUE, 'pending', CURRENT_TIMESTAMP - INTERVAL '3 hours', 72, 'Within 6 hours', NULL, NULL);

-- ============================================
-- TRIGGERS
-- ============================================

-- Update requests.updated_at on any update
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_requests_updated_at BEFORE UPDATE ON requests
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS
-- ============================================

-- View for pending requests sorted by priority
CREATE OR REPLACE VIEW pending_requests_by_priority AS
SELECT 
    request_id,
    citizen_name,
    email,
    phone,
    need_type,
    severity,
    priority_score,
    estimated_response_time,
    submitted_at
FROM requests
WHERE status = 'pending'
ORDER BY priority_score DESC, submitted_at ASC;

-- View for staff performance
CREATE OR REPLACE VIEW staff_performance AS
SELECT 
    s.staff_id,
    s.full_name,
    s.email,
    s.department,
    s.role,
    s.status,
    s.requests_handled,
    COUNT(r.request_id) AS current_assigned_requests
FROM staff s
LEFT JOIN requests r ON s.staff_id = r.assigned_staff_id AND r.status != 'completed'
GROUP BY s.staff_id, s.full_name, s.email, s.department, s.role, s.status, s.requests_handled
ORDER BY s.requests_handled DESC;

-- View for dashboard statistics
CREATE OR REPLACE VIEW dashboard_stats AS
SELECT 
    COUNT(*) FILTER (WHERE status = 'pending') AS pending_requests,
    COUNT(*) FILTER (WHERE status = 'in-progress') AS in_progress_requests,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_requests,
    COUNT(*) FILTER (WHERE severity = 'critical') AS critical_requests,
    COUNT(*) FILTER (WHERE is_student = TRUE) AS student_requests,
    COUNT(*) AS total_requests
FROM requests;

-- ============================================
-- VERIFICATION
-- ============================================
SELECT 'Database created successfully!' as status,
       (SELECT COUNT(*) FROM citizens) as total_citizens,
       (SELECT COUNT(*) FROM staff) as total_staff,
       (SELECT COUNT(*) FROM requests) as total_requests;

-- ============================================
-- TEST CREDENTIALS (All passwords: password123)
-- ============================================
-- CITIZENS:
--   john@example.com
--   sarah@example.com
--   maria@example.com
--
-- ADMIN:
--   john.administrator@gov.example.com (Full admin access)
--
-- STAFF:
--   sarah.mitchell@gov.example.com (Social Services Officer)
--   david.chen@gov.example.com (Emergency Services Coordinator)
--   maria.garcia@gov.example.com (Health & Medical Officer)
--   robert.taylor@gov.example.com (Education Services Analyst)
-- ============================================
