/** 智能数开 · 示例 ETL SQL 文件树（可后续对接真实仓库） */
export interface EtlFileNode {
  id: string;
  name: string;
  path: string;
  kind: 'folder' | 'file';
  language?: 'sql';
  content?: string;
  children?: EtlFileNode[];
}

export const ETL_FILE_TREE: EtlFileNode[] = [
  {
    id: 'ods',
    name: 'ods',
    path: 'ods',
    kind: 'folder',
    children: [
      {
        id: 'ods.order_sync',
        name: 'order_sync.sql',
        path: 'ods/order_sync.sql',
        kind: 'file',
        language: 'sql',
        content: `-- ODS · 订单增量同步
-- 源：业务库 order_detail → 贴源层
INSERT INTO tmp.ods_order_detail
SELECT
  o.order_id,
  o.user_id,
  o.order_amt,
  o.order_status,
  o.updated_at AS data_dt
FROM biz.order_detail o
WHERE o.updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);
`,
      },
      {
        id: 'ods.customer_sync',
        name: 'customer_sync.sql',
        path: 'ods/customer_sync.sql',
        kind: 'file',
        language: 'sql',
        content: `-- ODS · 客户主数据同步
INSERT INTO tmp.ods_customer
SELECT
  c.customer_id,
  c.customer_name,
  c.mobile_masked,
  c.updated_at AS data_dt
FROM biz.customer c
WHERE c.updated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);
`,
      },
    ],
  },
  {
    id: 'dwd',
    name: 'dwd',
    path: 'dwd',
    kind: 'folder',
    children: [
      {
        id: 'dwd.trade_order',
        name: 'trade_order.sql',
        path: 'dwd/trade_order.sql',
        kind: 'file',
        language: 'sql',
        content: `-- DWD · 交易订单明细
INSERT OVERWRITE TABLE tmp.dwd_trade_order
SELECT
  o.order_id,
  o.user_id,
  o.order_amt,
  CASE
    WHEN o.order_status IN ('PAID', 'DONE') THEN 'success'
    WHEN o.order_status = 'CANCEL' THEN 'cancel'
    ELSE 'other'
  END AS order_status_norm,
  o.data_dt
FROM tmp.ods_order_detail o
WHERE o.data_dt = CURRENT_DATE();
`,
      },
    ],
  },
  {
    id: 'ads',
    name: 'ads',
    path: 'ads',
    kind: 'folder',
    children: [
      {
        id: 'ads.gmv_daily',
        name: 'gmv_daily.sql',
        path: 'ads/gmv_daily.sql',
        kind: 'file',
        language: 'sql',
        content: `-- ADS · 日 GMV
INSERT OVERWRITE TABLE tmp.ads_gmv_daily
SELECT
  data_dt,
  COUNT(DISTINCT order_id) AS order_cnt,
  SUM(order_amt) AS gmv,
  SUM(order_amt) / NULLIF(COUNT(DISTINCT user_id), 0) AS arpu
FROM tmp.dwd_trade_order
WHERE order_status_norm = 'success'
GROUP BY data_dt;
`,
      },
    ],
  },
];

export function flattenEtlFiles(nodes: EtlFileNode[] = ETL_FILE_TREE): EtlFileNode[] {
  const out: EtlFileNode[] = [];
  const walk = (list: EtlFileNode[]) => {
    for (const n of list) {
      if (n.kind === 'file') out.push(n);
      if (n.children) walk(n.children);
    }
  };
  walk(nodes);
  return out;
}
