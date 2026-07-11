-- ============================================================
-- 客户中心 (CIF) —— sim_cust_cif
-- 存储客户主档、身份信息、地址、联系方式、KYC 结果、客户标签
-- ============================================================

DROP TABLE IF EXISTS customer_tag;
DROP TABLE IF EXISTS kyc_result;
DROP TABLE IF EXISTS contact;
DROP TABLE IF EXISTS address;
DROP TABLE IF EXISTS identity;
DROP TABLE IF EXISTS customer;

-- 客户主档
CREATE TABLE customer (
    customer_id VARCHAR(16) NOT NULL COMMENT '客户号 CXXXXXXXX',
    name VARCHAR(64) NOT NULL COMMENT '姓名（虚构）',
    gender TINYINT NOT NULL COMMENT '性别 1男 2女',
    birth_date DATE NOT NULL COMMENT '出生日期',
    age INT NOT NULL COMMENT '快照年龄（生成时）',
    education VARCHAR(16) NOT NULL COMMENT '学历 高中/大专/本科/硕士',
    marital VARCHAR(16) NOT NULL COMMENT '婚姻 未婚/已婚/离异',
    occupation VARCHAR(32) NOT NULL COMMENT '职业',
    monthly_income DECIMAL(12,2) NOT NULL COMMENT '月收入',
    reg_channel VARCHAR(32) NOT NULL COMMENT '注册渠道',
    reg_time DATETIME NOT NULL COMMENT '注册时间',
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态 ACTIVE/BLOCKED/CLOSED',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (customer_id),
    KEY idx_reg_time (reg_time),
    KEY idx_reg_channel (reg_channel)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户主档';

-- 身份信息
CREATE TABLE identity (
    customer_id VARCHAR(16) NOT NULL,
    id_type VARCHAR(8) NOT NULL DEFAULT 'ID' COMMENT '证件类型 ID=身份证',
    id_number VARCHAR(32) NOT NULL COMMENT '身份证号（虚构）',
    id_issue_org VARCHAR(64) COMMENT '签发机关',
    province VARCHAR(32) NOT NULL COMMENT '户籍省份',
    verified_at DATETIME COMMENT '实名认证时间',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (customer_id),
    KEY idx_province (province)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户身份信息';

-- 地址
CREATE TABLE address (
    address_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL,
    addr_type VARCHAR(16) NOT NULL COMMENT '类型 HOME/WORK/OTHER',
    province VARCHAR(32) NOT NULL,
    city VARCHAR(32) NOT NULL,
    district VARCHAR(64),
    detail VARCHAR(255),
    is_current TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (address_id),
    KEY idx_customer (customer_id, addr_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户地址';

-- 联系方式
CREATE TABLE contact (
    contact_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL,
    contact_type VARCHAR(16) NOT NULL COMMENT 'MOBILE/EMAIL/EMER',
    contact_value VARCHAR(128) NOT NULL COMMENT '手机号/邮箱/紧急联系人',
    contact_name VARCHAR(64) COMMENT '仅紧急联系人使用',
    contact_relation VARCHAR(32) COMMENT '仅紧急联系人使用',
    is_current TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (contact_id),
    KEY idx_customer (customer_id, contact_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户联系方式';

-- KYC 认证结果
CREATE TABLE kyc_result (
    kyc_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL,
    kyc_type VARCHAR(16) NOT NULL COMMENT 'REAL_NAME/FACE/BANK_CARD',
    result VARCHAR(16) NOT NULL COMMENT 'PASS/FAIL',
    fail_reason VARCHAR(128),
    completed_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (kyc_id),
    KEY idx_customer (customer_id, kyc_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT 'KYC 认证结果';

-- 客户标签
CREATE TABLE customer_tag (
    tag_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL,
    tag_code VARCHAR(32) NOT NULL COMMENT '标签编码 e.g. HIGH_QUALITY',
    tag_name VARCHAR(64) NOT NULL,
    tag_source VARCHAR(32) NOT NULL COMMENT 'MANUAL/MODEL/RULE',
    valid_from DATE NOT NULL,
    valid_to DATE,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (tag_id),
    KEY idx_customer_tag (customer_id, tag_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户标签';
