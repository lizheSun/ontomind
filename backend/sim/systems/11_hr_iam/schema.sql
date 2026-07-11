-- ============================================================
-- HR & 权限 —— sim_hr_iam
-- ============================================================

DROP TABLE IF EXISTS user_role;
DROP TABLE IF EXISTS role;
DROP TABLE IF EXISTS employee;
DROP TABLE IF EXISTS org_unit;

CREATE TABLE org_unit (
    org_code VARCHAR(16) NOT NULL,
    org_name VARCHAR(64) NOT NULL,
    parent_code VARCHAR(16),
    org_level TINYINT NOT NULL COMMENT '1总部 2一级部门 3二级部门',
    org_type VARCHAR(16) NOT NULL COMMENT 'HQ/BRANCH/DEPT',
    manager_emp_no VARCHAR(16),
    PRIMARY KEY (org_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '组织架构';

CREATE TABLE employee (
    emp_no VARCHAR(16) NOT NULL,
    name VARCHAR(64) NOT NULL,
    gender TINYINT NOT NULL,
    org_code VARCHAR(16) NOT NULL,
    position VARCHAR(64) NOT NULL,
    hire_date DATE NOT NULL,
    resign_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    email VARCHAR(128),
    phone VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (emp_no),
    KEY idx_org (org_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '员工';

CREATE TABLE role (
    role_code VARCHAR(32) NOT NULL,
    role_name VARCHAR(64) NOT NULL,
    description VARCHAR(255),
    PRIMARY KEY (role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '角色';

CREATE TABLE user_role (
    ur_id BIGINT NOT NULL AUTO_INCREMENT,
    emp_no VARCHAR(16) NOT NULL,
    role_code VARCHAR(32) NOT NULL,
    granted_at DATETIME NOT NULL,
    PRIMARY KEY (ur_id),
    UNIQUE KEY uk_emp_role (emp_no, role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '员工角色关系';
