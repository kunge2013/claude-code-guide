### 你是一个python高手

## 需求

1. 我现在需要写一个sq联查询工具 ， 查询 数据列表

2. sql查询分为三个模板

   实例信息: SELECT
   	t.remark,
   	t.OWNER_CUST_ID,
   	t.BELONG_ORG,
   	t.EXT_PROD_INST_ID,
   	t.cycle_type,
   	t.acct_id,
   	t.PROD_NAME,
   	t.prod_Id,
   	t.BILL_TYPE,
   	t.STOP_RENT_DATE,
   	t.BEGIN_RENT_CD,
   	t.STOP_RENT_CD,
   	t.Z_ORG_ID,
   	t.Z_LAN_ID,
   	t.A_ORG_ID,
   	t.A_LAN_ID,
   	t.NET_NBR,
   	t.* 
   FROM
   	prod_inst t 
   WHERE
   	prod_inst_id = '114435995';
   	
   变更日志: SELECT
   	PROD_INST_ID,
   	BEGIN_DATE,
   	INPUT_DATE,
   	ATTR_ID,
   	ATTR_NAME,
   	MOD_BEFORE,
   	MOD_AFTER,
   	MOD_BEFORE_VAL,
   	MOD_AFTER_VAL,
   	MOD_DATE,
   	MOD_REASON 
   FROM
   	prod_inst_log 
   WHERE
   	prod_inst_id = '114435995' 
   ORDER BY
   	AUD_DATE DESC;

   

   变更记录: SELECT
   	a.ACCT_ITEM_TYPE_ID,
   	b.NAME,
   	a.LOOP_MONEY,
   	a.START_DATE,
   	a.END_DATE,
   	a.START_FLAG,
   	a.LATEST_FLAG,
   	a.* 
   FROM
   	cal_acct_record a
   	LEFT JOIN acct_item_type b ON a.ACCT_ITEM_TYPE_ID = b.ACCT_ITEM_TYPE_ID 
   WHERE
   	PROD_INST_ID = '114435995' 
   ORDER BY
   	acct_item_type_id DESC,
   	start_date ASC;

数据库是mysql ， 界面可配置

输入条件 为 PROD_INST_ID 实例ID



请输出 python 以及界面， 我需要配置执行查询相关语句