-- ============================================================
-- DIM 层 ETL：6 步
-- 从 etl.py 抽出（去除注释、模板变量已替换为示例值）
-- 生产环境中，模板变量 ${today} / ${date} / ${month} 应由调度器填充
-- ============================================================

-- dim_date insert
INSERT INTO dim_date
        SELECT
            DATE_FORMAT(d, '%Y%m%d') + 0 AS date_key,
            d AS date_value,
            YEAR(d), QUARTER(d), MONTH(d), MONTHNAME(d),
            WEEK(d), DAY(d), DAYOFWEEK(d),
            IF(DAYOFWEEK(d) IN (1,7), 1, 0),
            0
        FROM (
            SELECT DATE('{DATE_START}') + INTERVAL n DAY AS d
            FROM (SELECT a.i + b.i*10 + c.i*100 + d.i*1000 AS n
                  FROM (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a,
                       (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b,
                       (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) c,
                       (SELECT 0 i UNION SELECT 1) d) t
            WHERE DATE('{DATE_START}') + INTERVAL n DAY <= '{DATE_END}'
        ) dates;

-- dim_customer insert
INSERT INTO dim_customer
          (customer_id, name, gender_code, gender_name, age, age_group,
           education, marital, occupation, monthly_income, income_grade,
           province, reg_channel, reg_date, status, valid_from, valid_to, is_current)
        SELECT c.customer_id, c.name, c.gender,
               CASE c.gender WHEN 1 THEN '男' WHEN 2 THEN '女' END,
               c.age,
               CASE
                 WHEN c.age < 26 THEN '18-25'
                 WHEN c.age < 36 THEN '26-35'
                 WHEN c.age < 46 THEN '36-45'
                 WHEN c.age < 56 THEN '46-55'
                 ELSE '55+' END,
               c.education, c.marital, c.occupation, c.monthly_income,
               CASE
                 WHEN c.monthly_income < 5000 THEN '低收入(<5k)'
                 WHEN c.monthly_income < 10000 THEN '中低(5-10k)'
                 WHEN c.monthly_income < 20000 THEN '中(10-20k)'
                 WHEN c.monthly_income < 50000 THEN '中高(20-50k)'
                 ELSE '高(50k+)' END,
               id.province, c.reg_channel, DATE(c.reg_time), c.status,
               c.reg_time, '9999-12-31 23:59:59', 1
        FROM sim_cust_cif.customer c
        LEFT JOIN sim_cust_cif.identity id ON id.customer_id = c.customer_id;

-- dim_product insert
INSERT INTO dim_product (product_code, product_name, product_kind,
                                  min_amount, max_amount, apr_default, is_active)
        SELECT product_code, product_name, product_kind,
               min_amount, max_amount, apr_default, is_active
        FROM sim_credit_core.product;

-- dim_channel insert
INSERT INTO dim_channel (channel_code, channel_name, channel_type, channel_owner)
        SELECT channel_code, channel_name, channel_type, channel_owner
        FROM sim_marketing.channel;

-- dim_org insert
INSERT INTO dim_org (org_code, org_name, parent_code, org_level, org_type)
        SELECT org_code, org_name, parent_code, org_level, org_type
        FROM sim_hr_iam.org_unit;

-- dim_funding_partner insert
INSERT INTO dim_funding_partner (partner_code, partner_name, partner_type)
        SELECT partner_code, partner_name, partner_type FROM sim_funding.funding_partner;

