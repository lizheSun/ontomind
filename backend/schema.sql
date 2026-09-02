-- OntoMind schema (ORM export)



CREATE TABLE agent_bundles (
	name VARCHAR(128) NOT NULL COMMENT '方案名', 
	description VARCHAR(1024) COMMENT '方案说明', 
	pattern VARCHAR(32) NOT NULL COMMENT '编排模式: single/plan-build/orchestrator-workers/research-loop/review-loop/pipeline/custom', 
	default_agent VARCHAR(64) COMMENT '默认 primary agent；OpenCode 要求必须是 primary，否则 fallback 到 build', 
	subagent_depth INTEGER COMMENT 'subagent 嵌套深度：0=禁止派生 / 1=默认 / 2=允许再嵌一层', 
	global_permission_json JSON COMMENT 'bundle 级全局 permission（如 skill 的 glob 白名单）', 
	topology_json JSON COMMENT '拓扑布局（前端 SVG 渲染用）', 
	is_builtin_preset BOOL NOT NULL COMMENT '内置预设（不可删除）', 
	current_version INTEGER NOT NULL COMMENT '当前版本号', 
	created_by_user_id INTEGER COMMENT '创建人', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	UNIQUE (name)
)COMMENT='Agent 编排方案表（Loop 模式，发布的原子单元）'



CREATE TABLE agent_template_versions (
	agent_template_id INTEGER NOT NULL COMMENT '所属 agent 模板', 
	version INTEGER NOT NULL COMMENT '版本号（从 1 递增）', 
	snapshot_json JSON NOT NULL COMMENT '该版本的完整配置快照', 
	change_note VARCHAR(512) COMMENT '变更说明', 
	created_by_user_id INTEGER COMMENT '操作人', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_agent_version UNIQUE (agent_template_id, version), 
	FOREIGN KEY(agent_template_id) REFERENCES agent_templates (id) ON DELETE CASCADE
)COMMENT='Agent 模板版本快照表'



CREATE TABLE agent_templates (
	name VARCHAR(64) NOT NULL COMMENT 'agent 名（=文件名，小写连字符）', 
	display_name VARCHAR(128) COMMENT '展示名', 
	description VARCHAR(1024) NOT NULL COMMENT '用途描述（决定自动委派）', 
	mode VARCHAR(16) NOT NULL COMMENT '模式: subagent / primary / all', 
	model VARCHAR(128) COMMENT 'provider/model-id，空=继承调用方', 
	prompt TEXT COMMENT 'system prompt（Markdown 正文）', 
	temperature FLOAT COMMENT '0.0-1.0', 
	top_p FLOAT COMMENT '0.0-1.0', 
	steps INTEGER COMMENT '迭代上限（maxSteps 已废弃）', 
	permission_json JSON COMMENT '权限配置（15 个合法键）', 
	options_json JSON COMMENT '透传给 provider 的额外参数', 
	color VARCHAR(32) COMMENT '#RRGGBB 或主题色名', 
	hidden BOOL NOT NULL COMMENT '是否从 @ 补全中隐藏', 
	disable BOOL NOT NULL COMMENT '是否禁用', 
	category VARCHAR(64) COMMENT '分类: review/security/docs/...', 
	is_builtin_preset BOOL NOT NULL COMMENT '内置预设（不可删除）', 
	source VARCHAR(16) NOT NULL COMMENT '来源: platform / imported / preset', 
	current_version INTEGER NOT NULL COMMENT '当前版本号', 
	created_by_user_id INTEGER COMMENT '创建人', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	UNIQUE (name)
)COMMENT='Agent 模板表（OpenCode agent 设计态）'



CREATE TABLE annotations (
	target_type ENUM('table','column') NOT NULL, 
	target_id INTEGER NOT NULL, 
	label_kind ENUM('biz_name','biz_description','domain','glossary','pii_level','join_key','entity_candidate','semantic_type') NOT NULL, 
	label_value TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	source ENUM('rule','llm','human') NOT NULL, 
	status ENUM('suggested','accepted','rejected','superseded') NOT NULL, 
	evidence_json JSON, 
	reviewed_by INTEGER, 
	reviewed_at DATETIME, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='元数据自动/人工标注'



CREATE TABLE audit_logs (
	actor_user_id INTEGER, 
	action VARCHAR(128) NOT NULL, 
	resource_type VARCHAR(64) NOT NULL, 
	resource_id VARCHAR(128), 
	outcome VARCHAR(32) NOT NULL, 
	details JSON, 
	request_id VARCHAR(128), 
	source_ip VARCHAR(64), 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
)COMMENT='Agent 平台安全审计日志'



CREATE TABLE bundle_members (
	bundle_id INTEGER NOT NULL COMMENT '所属 bundle', 
	member_type VARCHAR(16) NOT NULL COMMENT '成员类型: agent / skill', 
	agent_template_id INTEGER COMMENT 'agent 模板（member_type=agent）', 
	skill_template_id INTEGER COMMENT 'skill 模板（member_type=skill）', 
	`role` VARCHAR(16) NOT NULL COMMENT '角色: primary / subagent / skill', 
	skill_permission VARCHAR(8) COMMENT 'skill 成员的可见性: allow / ask / deny', 
	task_permission VARCHAR(8) COMMENT 'subagent 成员在本方案内的被委派权限: allow / ask / deny；空=继承模板', 
	sort_order INTEGER NOT NULL COMMENT '排序（pipeline 模式下决定串行顺序）', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_bundle_member UNIQUE (bundle_id, member_type, agent_template_id, skill_template_id), 
	FOREIGN KEY(bundle_id) REFERENCES agent_bundles (id) ON DELETE CASCADE, 
	FOREIGN KEY(agent_template_id) REFERENCES agent_templates (id) ON DELETE CASCADE, 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Bundle 成员表'



CREATE TABLE compute_nodes (
	name VARCHAR(128) NOT NULL COMMENT '节点名称', 
	description VARCHAR(512) COMMENT '节点描述', 
	host VARCHAR(256) NOT NULL COMMENT '主机地址/IP', 
	port INTEGER NOT NULL COMMENT 'SSH 端口', 
	username VARCHAR(128) NOT NULL COMMENT 'SSH 用户名', 
	auth_type ENUM('password','key') NOT NULL COMMENT '认证方式: password / key', 
	password TEXT COMMENT 'SSH 密码（AES 加密存储）', 
	private_key TEXT COMMENT 'SSH 私钥（AES 加密存储）', 
	is_local BOOL NOT NULL COMMENT '是否本地节点', 
	status ENUM('online','offline','unknown') NOT NULL COMMENT '节点状态: online / offline / unknown', 
	last_checked_at DATETIME COMMENT '最后探活时间', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	UNIQUE (name)
)COMMENT='算力节点表'



CREATE TABLE container_services (
	node_id INTEGER NOT NULL COMMENT '所属算力节点', 
	node_name VARCHAR(128) NOT NULL COMMENT '节点名称快照（避免每次 join）', 
	container_id VARCHAR(64) NOT NULL COMMENT '容器 ID（短 ID）', 
	container_name VARCHAR(255) NOT NULL COMMENT '容器名称', 
	image VARCHAR(512) COMMENT '容器镜像', 
	kind ENUM('opencode_web','opencode_serve','dsh_web','other') NOT NULL COMMENT '服务类型: opencode_web / opencode_serve / dsh_web / other', 
	name VARCHAR(128) NOT NULL COMMENT '服务显示名', 
	container_port INTEGER NOT NULL COMMENT '容器内监听端口', 
	host_port INTEGER COMMENT '映射到宿主的端口（无映射则为 NULL）', 
	access_url VARCHAR(512) COMMENT '宿主可访问 URL', 
	command TEXT COMMENT '启动该服务的完整命令', 
	log_path VARCHAR(512) COMMENT '容器内日志文件路径', 
	exec_id VARCHAR(32) COMMENT '启动时的 exec 会话 ID', 
	status ENUM('running','stopped','unreachable','unknown') NOT NULL COMMENT '探测状态: running / stopped / unreachable / unknown', 
	status_detail VARCHAR(512) COMMENT '状态说明（失败原因等）', 
	bind_address VARCHAR(64) COMMENT '实际监听地址（0.0.0.0 / 127.0.0.1）', 
	host_reachable BOOL NOT NULL COMMENT '宿主能否访问（access_url 探测结果）', 
	last_checked_at DATETIME COMMENT '最后探测时间', 
	is_aide_source BOOL NOT NULL COMMENT '是否可作为 AIDE 嵌入源（opencode 类 + 宿主可达）', 
	created_by_user_id INTEGER COMMENT '登记人', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_container_port UNIQUE (container_id, container_port), 
	FOREIGN KEY(node_id) REFERENCES compute_nodes (id) ON DELETE CASCADE
)COMMENT='容器服务登记表（opencode web/serve、DeepSeek Harness web 等常驻服务）'



CREATE TABLE data_sources (
	name VARCHAR(128) NOT NULL COMMENT '显示名称', 
	source_type ENUM('doris','mysql','hive') NOT NULL COMMENT 'doris / mysql / hive', 
	host VARCHAR(256) NOT NULL COMMENT '主机', 
	port INTEGER NOT NULL COMMENT '端口', 
	username VARCHAR(128) NOT NULL COMMENT '用户名', 
	password TEXT COMMENT '密码（服务端存储）', 
	`database` VARCHAR(128) COMMENT '默认库', 
	charset VARCHAR(32) NOT NULL COMMENT '字符集', 
	description VARCHAR(512) COMMENT '备注', 
	status ENUM('unknown','online','offline') NOT NULL COMMENT '最近探活状态', 
	is_default BOOL NOT NULL COMMENT '是否默认种子源', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	UNIQUE (name)
)COMMENT='DataOps 数据源'



CREATE TABLE deployments (
	bundle_id INTEGER NOT NULL COMMENT '发布的 bundle', 
	bundle_name VARCHAR(128) NOT NULL COMMENT 'bundle 名快照', 
	bundle_version INTEGER NOT NULL COMMENT '发布时的 bundle 版本', 
	node_id INTEGER NOT NULL COMMENT '目标算力节点', 
	node_name VARCHAR(128) NOT NULL COMMENT '节点名快照', 
	container_id VARCHAR(64) NOT NULL COMMENT '目标容器 ID', 
	container_name VARCHAR(255) NOT NULL COMMENT '容器名快照', 
	scope VARCHAR(16) NOT NULL COMMENT '范围: global / project', 
	target_dir VARCHAR(512) NOT NULL COMMENT '容器内目标目录', 
	status VARCHAR(16) NOT NULL COMMENT '状态', 
	artifacts_json JSON COMMENT '产物清单（含 sha256，用于幂等与漂移检测）', 
	verify_json JSON COMMENT '回读校验结果（期望 vs 容器实际）', 
	restart_used BOOL NOT NULL COMMENT '是否重启了容器内服务', 
	error_detail TEXT COMMENT '失败原因（可执行的中文提示）', 
	duration_ms INTEGER COMMENT '总耗时', 
	deployed_by_user_id INTEGER COMMENT '发布人', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(bundle_id) REFERENCES agent_bundles (id) ON DELETE CASCADE, 
	FOREIGN KEY(node_id) REFERENCES compute_nodes (id) ON DELETE CASCADE
)COMMENT='Bundle 发布记录表（含产物清单与回读校验结果）'



CREATE TABLE glossary_terms (
	name VARCHAR(128) NOT NULL, 
	aliases_json JSON, 
	definition TEXT, 
	domain VARCHAR(128), 
	source_type ENUM('rules','llm','manual') NOT NULL, 
	source_doc_id INTEGER, 
	confidence FLOAT, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_doc_id) REFERENCES wiki_documents (id) ON DELETE SET NULL
)COMMENT='业务术语表'



CREATE TABLE meta_column_standard_history (
	column_id INTEGER NOT NULL, 
	standard_id INTEGER, 
	standard_version INTEGER, 
	action VARCHAR(32) NOT NULL, 
	snapshot_json JSON, 
	actor_user_id INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(column_id) REFERENCES meta_columns (id) ON DELETE CASCADE, 
	FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='字段标准绑定审计'



CREATE TABLE meta_column_standards (
	column_id INTEGER NOT NULL, 
	standard_id INTEGER NOT NULL, 
	standard_version INTEGER NOT NULL, 
	security_level_override VARCHAR(8), 
	status ENUM('suggested','accepted','rejected') NOT NULL, 
	source ENUM('rule','llm','human') NOT NULL, 
	confidence FLOAT, 
	evidence_json JSON, 
	reviewed_by INTEGER, 
	reviewed_at DATETIME, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meta_column_standard_column UNIQUE (column_id), 
	FOREIGN KEY(column_id) REFERENCES meta_columns (id) ON DELETE CASCADE, 
	FOREIGN KEY(standard_id) REFERENCES meta_standards (id) ON DELETE RESTRICT, 
	FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='字段标准绑定（字段 1:1 标准；标准 1:N 字段）'



CREATE TABLE meta_columns (
	table_id INTEGER NOT NULL, 
	column_name VARCHAR(128) NOT NULL, 
	ordinal INTEGER NOT NULL, 
	data_type VARCHAR(64), 
	column_type VARCHAR(128), 
	nullable BOOL NOT NULL, 
	column_key VARCHAR(16), 
	column_default TEXT, 
	extra VARCHAR(128), 
	column_comment TEXT, 
	biz_name VARCHAR(128), 
	biz_description TEXT, 
	semantic_type VARCHAR(64), 
	pii_level VARCHAR(8), 
	profile_json JSON, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meta_column UNIQUE (table_id, column_name), 
	FOREIGN KEY(table_id) REFERENCES meta_tables (id) ON DELETE CASCADE
)COMMENT='元数据列快照'



CREATE TABLE meta_database_briefs (
	source_id INTEGER NOT NULL, 
	`database` VARCHAR(128) NOT NULL, 
	mode VARCHAR(16) NOT NULL, 
	content_md TEXT, 
	stats_json JSON, 
	job_id INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meta_database_brief UNIQUE (source_id, `database`), 
	FOREIGN KEY(source_id) REFERENCES data_sources (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES meta_scan_jobs (id) ON DELETE SET NULL
)COMMENT='库级智能/规则分析概况'



CREATE TABLE meta_scan_jobs (
	source_id INTEGER NOT NULL, 
	`database` VARCHAR(128) NOT NULL, 
	job_kind ENUM('scan','annotate','brief') NOT NULL, 
	status ENUM('pending','running','succeeded','failed') NOT NULL, 
	progress FLOAT NOT NULL, 
	with_profile BOOL NOT NULL, 
	mode VARCHAR(16), 
	tables_json JSON, 
	stats_json JSON, 
	error_detail TEXT, 
	duration_ms INTEGER, 
	started_at DATETIME, 
	finished_at DATETIME, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (id) ON DELETE CASCADE
)COMMENT='元数据扫描/标注任务'



CREATE TABLE meta_standard_versions (
	standard_id INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	snapshot_json JSON NOT NULL, 
	change_note VARCHAR(512), 
	author_user_id INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meta_standard_version UNIQUE (standard_id, version), 
	FOREIGN KEY(standard_id) REFERENCES meta_standards (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_user_id) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='标准项版本快照'



CREATE TABLE meta_standards (
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	aliases_json JSON, 
	description TEXT, 
	semantic_type VARCHAR(64), 
	data_type_expect VARCHAR(64), 
	length_rule_json JSON, 
	security_level VARCHAR(8) NOT NULL, 
	quality_rule_json JSON, 
	mask_rule VARCHAR(64), 
	domain VARCHAR(128), 
	status ENUM('draft','published') NOT NULL, 
	current_version INTEGER NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id)
)COMMENT='元数据标准项（一标准可绑多字段）'



CREATE TABLE meta_tables (
	source_id INTEGER NOT NULL, 
	`database` VARCHAR(128) NOT NULL, 
	table_name VARCHAR(128) NOT NULL, 
	table_type VARCHAR(64), 
	table_comment TEXT, 
	row_count INTEGER, 
	engine VARCHAR(64), 
	biz_name VARCHAR(128), 
	biz_description TEXT, 
	domain VARCHAR(128), 
	column_count INTEGER, 
	profiled_at DATETIME, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meta_table UNIQUE (source_id, `database`, table_name), 
	FOREIGN KEY(source_id) REFERENCES data_sources (id) ON DELETE CASCADE
)COMMENT='元数据表快照'



CREATE TABLE ontologies (
	name VARCHAR(128) NOT NULL, 
	slug VARCHAR(64) NOT NULL, 
	description VARCHAR(512), 
	domain VARCHAR(128), 
	current_version INTEGER NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id)
)COMMENT='本体'



CREATE TABLE ontology_build_jobs (
	ontology_id INTEGER NOT NULL, 
	status ENUM('pending','running','succeeded','failed') NOT NULL, 
	phase ENUM('extract','align','judge','merge','done') NOT NULL, 
	mode VARCHAR(16) NOT NULL, 
	scope_json JSON, 
	batch_size INTEGER NOT NULL, 
	progress FLOAT NOT NULL, 
	delta_json JSON, 
	error_detail TEXT, 
	duration_ms INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id) ON DELETE CASCADE
)COMMENT='本体构建任务'



CREATE TABLE ontology_cqs (
	ontology_id INTEGER NOT NULL, 
	question TEXT NOT NULL, 
	category VARCHAR(64), 
	verify_status ENUM('pass','fail','pending') NOT NULL, 
	verify_note TEXT, 
	related_keys_json JSON, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id) ON DELETE CASCADE
)COMMENT='Competency Questions'



CREATE TABLE ontology_link_types (
	ontology_id INTEGER NOT NULL, 
	`key` VARCHAR(128) NOT NULL, 
	display_name VARCHAR(256) NOT NULL, 
	from_key VARCHAR(128) NOT NULL, 
	to_key VARCHAR(128) NOT NULL, 
	cardinality VARCHAR(16), 
	definition TEXT, 
	confidence FLOAT NOT NULL, 
	source ENUM('rule','llm','human') NOT NULL, 
	status ENUM('draft','accepted','rejected') NOT NULL, 
	evidence_json JSON, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ontology_link_type_key UNIQUE (ontology_id, `key`), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id) ON DELETE CASCADE
)COMMENT='本体关系类型'



CREATE TABLE ontology_mappings (
	ontology_id INTEGER NOT NULL, 
	element_type ENUM('object_type','property','link_type') NOT NULL, 
	element_key VARCHAR(128) NOT NULL, 
	source_id INTEGER NOT NULL, 
	`database` VARCHAR(128) NOT NULL, 
	table_name VARCHAR(128) NOT NULL, 
	column_name VARCHAR(128), 
	confidence FLOAT NOT NULL, 
	source ENUM('rule','llm','human') NOT NULL, 
	status ENUM('draft','accepted','rejected') NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id) ON DELETE CASCADE, 
	FOREIGN KEY(source_id) REFERENCES data_sources (id) ON DELETE CASCADE
)COMMENT='本体到物理表映射'



CREATE TABLE ontology_metrics (
	ontology_id INTEGER NOT NULL, 
	`key` VARCHAR(128) NOT NULL, 
	display_name VARCHAR(256) NOT NULL, 
	definition TEXT, 
	sql_expr TEXT, 
	unit VARCHAR(64), 
	confidence FLOAT NOT NULL, 
	source ENUM('rule','llm','human') NOT NULL, 
	status ENUM('draft','accepted','rejected') NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ontology_metric_key UNIQUE (ontology_id, `key`), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id) ON DELETE CASCADE
)COMMENT='本体指标（语义层）'



CREATE TABLE ontology_object_types (
	ontology_id INTEGER NOT NULL, 
	`key` VARCHAR(128) NOT NULL, 
	display_name VARCHAR(256) NOT NULL, 
	definition TEXT, 
	parent_key VARCHAR(128), 
	aliases_json JSON, 
	confidence FLOAT NOT NULL, 
	source ENUM('rule','llm','human') NOT NULL, 
	status ENUM('draft','accepted','rejected') NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ontology_object_type_key UNIQUE (ontology_id, `key`), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id) ON DELETE CASCADE
)COMMENT='本体对象类型'



CREATE TABLE ontology_properties (
	ontology_id INTEGER NOT NULL, 
	object_type_id INTEGER NOT NULL, 
	`key` VARCHAR(128) NOT NULL, 
	display_name VARCHAR(256) NOT NULL, 
	data_type VARCHAR(64), 
	definition TEXT, 
	confidence FLOAT NOT NULL, 
	source ENUM('rule','llm','human') NOT NULL, 
	status ENUM('draft','accepted','rejected') NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ontology_property_key UNIQUE (object_type_id, `key`), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id) ON DELETE CASCADE, 
	FOREIGN KEY(object_type_id) REFERENCES ontology_object_types (id) ON DELETE CASCADE
)COMMENT='本体属性'



CREATE TABLE ontology_versions (
	ontology_id INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	snapshot_json JSON NOT NULL, 
	diff_json JSON, 
	change_note VARCHAR(512), 
	author_user_id INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ontology_version UNIQUE (ontology_id, version), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_user_id) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='本体版本快照'



CREATE TABLE platform_llm_settings (
	name VARCHAR(128) NOT NULL, 
	base_url VARCHAR(512) NOT NULL, 
	model VARCHAR(128) NOT NULL, 
	api_key_encrypted TEXT, 
	timeout INTEGER NOT NULL, 
	max_concurrency INTEGER NOT NULL, 
	enabled BOOL NOT NULL, 
	is_default BOOL NOT NULL, 
	updated_by INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(updated_by) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='平台 LLM 配置（支持多套，is_default 标记当前生效）'



CREATE TABLE roles (
	name VARCHAR(64) NOT NULL, 
	description VARCHAR(256), 
	is_system BOOL NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id)
)COMMENT='Agent 平台角色'



CREATE TABLE skill_audit_logs (
	skill_template_id INTEGER NOT NULL, 
	skill_name VARCHAR(64) NOT NULL COMMENT 'skill 名快照', 
	action VARCHAR(32) NOT NULL COMMENT 'create/update/lifecycle/snapshot/rollback/export/clone/delete', 
	field_path VARCHAR(128) COMMENT '变更字段路径，如 meta.qps_limit', 
	before_json JSON, 
	after_json JSON, 
	summary VARCHAR(512) COMMENT '人类可读的变更摘要', 
	operator_user_id INTEGER, 
	operator_name VARCHAR(64), 
	operator_ip VARCHAR(64), 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Skill 配置变更审计日志表（模块6）'



CREATE TABLE skill_exec_api (
	skill_template_id INTEGER NOT NULL, 
	http_method VARCHAR(8) NOT NULL, 
	url_test VARCHAR(1024) COMMENT '测试环境地址', 
	url_staging VARCHAR(1024) COMMENT '预发环境地址', 
	url_prod VARCHAR(1024) COMMENT '生产环境地址', 
	headers_json JSON COMMENT '静态请求头（禁含密钥）', 
	auth_type VARCHAR(16) NOT NULL COMMENT 'none/bearer/ak_sk/api_key/basic', 
	secret_ref VARCHAR(256) COMMENT '配置中心引用键，如 cc://skill/<name>/aksk —— 禁止明文密钥', 
	param_mapping_json JSON COMMENT '入参→请求字段映射 {paramName: {in: query|body|header|path, field}}', 
	timeout_ms INTEGER NOT NULL, 
	retry_times INTEGER NOT NULL, 
	retry_backoff_ms INTEGER NOT NULL, 
	success_path VARCHAR(256) COMMENT '判定成功的 JSONPath，如 $.code', 
	success_value VARCHAR(64) COMMENT '成功时该路径的期望值，如 0', 
	data_path VARCHAR(256) COMMENT '业务数据 JSONPath，如 $.data', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_exec_api_tpl UNIQUE (skill_template_id), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='API 调用型执行配置（模块3）；密钥仅存配置中心引用键'



CREATE TABLE skill_exec_flow_nodes (
	skill_template_id INTEGER NOT NULL, 
	node_key VARCHAR(64) NOT NULL COMMENT '节点唯一键（流程内）', 
	node_type VARCHAR(16) NOT NULL COMMENT 'start/skill/branch/loop/end', 
	label VARCHAR(128) COMMENT '节点显示名', 
	ref_skill_id INTEGER COMMENT '引用的原子 Skill', 
	condition_expr VARCHAR(512) COMMENT 'branch 的判断表达式', 
	loop_config_json JSON COMMENT 'loop 配置 {over: varName, maxIter: 10}', 
	var_mapping_json JSON COMMENT '上下游变量透传映射 {targetParam: sourceExpr}', 
	next_keys_json JSON COMMENT '后继节点键数组（branch 可多个）', 
	on_fail_next VARCHAR(64) COMMENT '失败跳转的节点键', 
	pos_x FLOAT COMMENT '画布坐标 X', 
	pos_y FLOAT COMMENT '画布坐标 Y', 
	sort_order INTEGER NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_flow_node UNIQUE (skill_template_id, node_key), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE, 
	FOREIGN KEY(ref_skill_id) REFERENCES skill_templates (id) ON DELETE SET NULL
)COMMENT='编排型流程节点（模块3）'



CREATE TABLE skill_exec_prompt (
	skill_template_id INTEGER NOT NULL, 
	system_prompt TEXT COMMENT '系统提示词', 
	few_shots_json JSON COMMENT '[{input, output}] 示例', 
	output_constraint TEXT COMMENT '输出约束规则', 
	output_format VARCHAR(16) NOT NULL COMMENT 'text/json/markdown', 
	temperature FLOAT, 
	max_tokens INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_exec_prompt_tpl UNIQUE (skill_template_id), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Prompt 推理型执行配置（模块3）'



CREATE TABLE skill_files (
	skill_template_id INTEGER NOT NULL COMMENT '所属 skill 模板', 
	rel_path VARCHAR(512) NOT NULL COMMENT '相对路径（禁止 .. 与绝对路径）', 
	content TEXT COMMENT '文件内容', 
	is_executable BOOL NOT NULL COMMENT '是否可执行（脚本落盘时给 0o755）', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_skill_file_path UNIQUE (skill_template_id, rel_path), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Skill 附属文件表（支撑渐进披露的多文件结构）'



CREATE TABLE skill_invocations (
	trace_id VARCHAR(64) NOT NULL COMMENT '全链路 trace id', 
	skill_template_id INTEGER NOT NULL, 
	skill_name VARCHAR(64) NOT NULL, 
	skill_version INTEGER, 
	agent_name VARCHAR(64) COMMENT '调用方智能体', 
	session_id VARCHAR(128), 
	account_id VARCHAR(128), 
	env VARCHAR(16) COMMENT 'test/staging/prod', 
	status VARCHAR(24) NOT NULL COMMENT 'success/param_error/network_error/service_error/timeout/circuit_open/denied', 
	error_code VARCHAR(64), 
	error_msg VARCHAR(1024), 
	input_json JSON COMMENT '入参（已脱敏）', 
	output_json JSON COMMENT '出参（已脱敏）', 
	duration_ms INTEGER, 
	retry_count INTEGER NOT NULL, 
	fallback_used BOOL NOT NULL, 
	is_canary BOOL NOT NULL COMMENT '是否灰度流量', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_invocation_trace UNIQUE (trace_id), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Skill 调用 Trace 表（模块7）'



CREATE TABLE skill_meta (
	skill_template_id INTEGER NOT NULL COMMENT '所属 skill 定义', 
	skill_kind VARCHAR(16) NOT NULL COMMENT '形态: prompt / api / flow', 
	name_zh VARCHAR(128) COMMENT '中文名', 
	name_en VARCHAR(128) COMMENT '英文名', 
	biz_tags_json JSON COMMENT '业务标签数组', 
	risk_level VARCHAR(16) NOT NULL COMMENT '风险等级: low(低危查询) / medium / high(高危资金操作)', 
	owner VARCHAR(64) COMMENT '责任人', 
	owner_email VARCHAR(128) COMMENT '责任人邮箱', 
	biz_line VARCHAR(64) COMMENT '归属业务线', 
	qps_limit INTEGER COMMENT '限流 QPS，空=不限', 
	session_call_limit INTEGER COMMENT '单会话调用频次上限，空=不限', 
	lifecycle VARCHAR(16) NOT NULL COMMENT '生命周期: draft/testing/canary/released/frozen/archived', 
	lifecycle_note VARCHAR(512) COMMENT '最近一次状态变更说明', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_skill_meta_tpl UNIQUE (skill_template_id), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Skill 治理元数据表（模块1）'



CREATE TABLE skill_params (
	skill_template_id INTEGER NOT NULL, 
	direction VARCHAR(8) NOT NULL COMMENT 'in / out', 
	name VARCHAR(64) NOT NULL COMMENT '参数名（合法标识符）', 
	title VARCHAR(128) COMMENT '展示名', 
	description VARCHAR(512) COMMENT '说明（会进 JSON Schema）', 
	data_type VARCHAR(16) NOT NULL COMMENT 'string/number/integer/boolean/object/array', 
	required BOOL NOT NULL, 
	default_value VARCHAR(512) COMMENT '默认值（字符串形式，按类型转换）', 
	enum_json JSON COMMENT '枚举可选值数组', 
	regex_pattern VARCHAR(512) COMMENT '正则校验（仅 string）', 
	min_val FLOAT COMMENT '最小值/最短长度', 
	max_val FLOAT COMMENT '最大值/最长长度', 
	source VARCHAR(16) COMMENT '来源: dialog(对话抽取)/context(会话变量)/system(内置)/const', 
	context_key VARCHAR(128) COMMENT 'source=context 时读的会话变量名', 
	const_value VARCHAR(512) COMMENT 'source=const 时的固定值', 
	mask_rule VARCHAR(16) NOT NULL COMMENT '脱敏规则', 
	mask_pattern VARCHAR(512) COMMENT 'custom 脱敏的正则', 
	filtered BOOL NOT NULL COMMENT '是否过滤掉不返回给模型（敏感字段只落 Trace 不出参）', 
	write_to_context BOOL NOT NULL COMMENT '是否写回会话上下文', 
	context_write_key VARCHAR(128) COMMENT '写回的会话变量名', 
	sort_order INTEGER NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_skill_param UNIQUE (skill_template_id, direction, name), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Skill 参数契约表（模块2）'



CREATE TABLE skill_policy (
	skill_template_id INTEGER NOT NULL, 
	timeout_ms INTEGER COMMENT '整体超时（覆盖执行配置）', 
	retry_times INTEGER COMMENT '重试次数', 
	circuit_threshold INTEGER COMMENT '熔断阈值：窗口内失败率百分比，如 50', 
	circuit_window_sec INTEGER COMMENT '统计窗口秒', 
	circuit_min_calls INTEGER COMMENT '窗口内最小样本数（避免小样本误熔断）', 
	circuit_cooldown_sec INTEGER COMMENT '熔断冷却秒', 
	fallback_mode VARCHAR(16) NOT NULL COMMENT '降级方式: none/static/skill/prompt', 
	fallback_payload TEXT COMMENT 'static 兜底内容 / skill 名 / prompt', 
	error_map_json JSON COMMENT '[{match, scene(param|network|service), user_msg, suggest}]', 
	allowed_agents_json JSON COMMENT '可调用的智能体名单（空=不限）', 
	allowed_roles_json JSON COMMENT '可调用的业务角色（RBAC）', 
	require_confirm BOOL NOT NULL COMMENT '高危技能二次确认开关', 
	confirm_prompt VARCHAR(512) COMMENT '二次确认话术', 
	account_whitelist_json JSON COMMENT '账号白名单（非空=仅这些可调）', 
	account_blacklist_json JSON COMMENT '账号黑名单', 
	ctx_read_keys_json JSON COMMENT '允许读取的会话变量键', 
	ctx_write_keys_json JSON COMMENT '允许写入的会话变量键', 
	session_isolation VARCHAR(16) NOT NULL COMMENT '会话数据隔离级别: none/session/account/tenant', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_skill_policy_tpl UNIQUE (skill_template_id), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Skill 治理策略表（模块4 容错熔断 + 模块5 安全权限）'



CREATE TABLE skill_templates (
	name VARCHAR(64) NOT NULL COMMENT 'skill 名（=目录名，小写连字符）', 
	description VARCHAR(1024) NOT NULL COMMENT '用途描述（模型选择依据，≤1024）', 
	license VARCHAR(64) COMMENT '许可证，如 MIT', 
	compatibility VARCHAR(128) COMMENT '兼容性声明，如 opencode', 
	metadata_json JSON COMMENT 'metadata（string→string 映射）', 
	body TEXT COMMENT 'SKILL.md 正文（frontmatter 之后的 Markdown）', 
	display_name VARCHAR(128) COMMENT '展示名', 
	category VARCHAR(64) COMMENT '分类', 
	is_builtin_preset BOOL NOT NULL COMMENT '内置预设（不可删除）', 
	source VARCHAR(16) NOT NULL COMMENT '来源', 
	current_version INTEGER NOT NULL COMMENT '当前版本号', 
	created_by_user_id INTEGER COMMENT '创建人', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	UNIQUE (name)
)COMMENT='Skill 模板表（OpenCode SKILL.md 设计态）'



CREATE TABLE skill_versions (
	skill_template_id INTEGER NOT NULL, 
	version INTEGER NOT NULL COMMENT '版本号（从 1 递增）', 
	snapshot_json JSON NOT NULL COMMENT '全配置快照（定义+元数据+参数+执行+策略）', 
	change_note VARCHAR(512), 
	lifecycle_at_snapshot VARCHAR(16) COMMENT '快照时的生命周期', 
	canary_json JSON COMMENT '灰度配置 {mode: percent|whitelist, percent: 10, accounts: [...]}', 
	created_by_user_id INTEGER, 
	created_by_name VARCHAR(64), 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_skill_version UNIQUE (skill_template_id, version), 
	FOREIGN KEY(skill_template_id) REFERENCES skill_templates (id) ON DELETE CASCADE
)COMMENT='Skill 全配置快照表（模块6）'



CREATE TABLE user_roles (
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	assigned_by_user_id INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_roles_user_role UNIQUE (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(assigned_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='用户角色关联'



CREATE TABLE users (
	username VARCHAR(50) NOT NULL COMMENT '用户名', 
	email VARCHAR(100) NOT NULL COMMENT '邮箱', 
	password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希', 
	full_name VARCHAR(100) COMMENT '全名', 
	is_active BOOL NOT NULL COMMENT '是否激活', 
	is_superuser BOOL NOT NULL COMMENT '是否超级管理员', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id)
)COMMENT='用户表'



CREATE TABLE wiki_document_versions (
	document_id INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	content_md TEXT NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	change_note VARCHAR(512), 
	author_user_id INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_wiki_doc_version UNIQUE (document_id, version), 
	FOREIGN KEY(document_id) REFERENCES wiki_documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_user_id) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='Wiki 文档版本快照'



CREATE TABLE wiki_documents (
	space_id INTEGER NOT NULL, 
	parent_id INTEGER, 
	title VARCHAR(256) NOT NULL, 
	slug VARCHAR(128) NOT NULL, 
	content_md TEXT NOT NULL, 
	source_type ENUM('paste','markdown','url','manual') NOT NULL, 
	source_url VARCHAR(1024), 
	source_meta_json JSON, 
	tags_json JSON, 
	status ENUM('draft','published') NOT NULL, 
	current_version INTEGER NOT NULL, 
	word_count INTEGER NOT NULL, 
	author_user_id INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(space_id) REFERENCES wiki_spaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(parent_id) REFERENCES wiki_documents (id) ON DELETE SET NULL, 
	FOREIGN KEY(author_user_id) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='Wiki 文档'



CREATE TABLE wiki_spaces (
	name VARCHAR(128) NOT NULL, 
	slug VARCHAR(64) NOT NULL, 
	description VARCHAR(512), 
	icon VARCHAR(32), 
	sort_order INTEGER NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id)
)COMMENT='Wiki 空间'

CREATE TABLE harness_sessions (
	user_id INTEGER NOT NULL,
	title VARCHAR(256) NOT NULL,
	plugin_id VARCHAR(32) NOT NULL,
	plugin_session_id VARCHAR(128),
	workspace_path VARCHAR(1024) NOT NULL,
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT,
	created_at DATETIME COMMENT '创建时间' DEFAULT now(),
	updated_at DATETIME COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)COMMENT='统一会话（OpenCode / DSH 插件）'

CREATE TABLE harness_messages (
	session_id INTEGER NOT NULL,
	role VARCHAR(16) NOT NULL,
	parts_json JSON NOT NULL,
	error_text TEXT,
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT,
	created_at DATETIME COMMENT '创建时间' DEFAULT now(),
	updated_at DATETIME COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(session_id) REFERENCES harness_sessions (id) ON DELETE CASCADE
)COMMENT='统一会话消息（parts JSON）'

CREATE TABLE kanban_boards (
	user_id INTEGER NOT NULL,
	name VARCHAR(128) NOT NULL,
	icon VARCHAR(32),
	color VARCHAR(20),
	position INTEGER NOT NULL,
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT,
	created_at DATETIME COMMENT '创建时间' DEFAULT now(),
	updated_at DATETIME COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)COMMENT='任务看板'

CREATE TABLE kanban_columns (
	board_id INTEGER NOT NULL,
	name VARCHAR(128) NOT NULL,
	icon VARCHAR(32),
	color VARCHAR(20),
	position INTEGER NOT NULL,
	collapsed BOOLEAN NOT NULL,
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT,
	created_at DATETIME COMMENT '创建时间' DEFAULT now(),
	updated_at DATETIME COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(board_id) REFERENCES kanban_boards (id) ON DELETE CASCADE
)COMMENT='看板列'

CREATE TABLE kanban_tasks (
	board_id INTEGER NOT NULL,
	column_id INTEGER,
	session_id INTEGER,
	title VARCHAR(256) NOT NULL,
	plugin_id VARCHAR(32) NOT NULL,
	run_status VARCHAR(16) NOT NULL,
	position INTEGER NOT NULL,
	summary TEXT,
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT,
	created_at DATETIME COMMENT '创建时间' DEFAULT now(),
	updated_at DATETIME COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(board_id) REFERENCES kanban_boards (id) ON DELETE CASCADE,
	FOREIGN KEY(column_id) REFERENCES kanban_columns (id) ON DELETE SET NULL,
	FOREIGN KEY(session_id) REFERENCES harness_sessions (id) ON DELETE SET NULL
)COMMENT='看板任务（可绑定统一会话）'

