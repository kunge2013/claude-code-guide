### 数据优化提示词fewshort 生成

### 1. 帮我读取check_record_results.xlsx ，且查询每个实例 日志数据和业务数据

业务数据:

SELECT a.ACCT_ITEM_TYPE_ID, a.ID, a.PROD_INST_ID, b.NAME, a.START_DATE,
                   a.END_DATE, a.START_FLAG, a.LATEST_FLAG, a.LOOP_MONEY,
                   a.CAL_ACCT_RECORD_ID, a.ACCT_ID, a.CREATE_DATE, a.UPDATE_DATE
            FROM cal_acct_record a
            LEFT JOIN acct_item_type b ON a.ACCT_ITEM_TYPE_ID = b.ACCT_ITEM_TYPE_ID
            WHERE a.PROD_INST_ID = '207120377'
            ORDER BY a.ACCT_ITEM_TYPE_ID DESC, a.START_DATE ASC

日志数据：

SELECT PROD_INST_ID, BEGIN_DATE, INPUT_DATE, ATTR_ID, ATTR_NAME,
                   MOD_BEFORE, MOD_AFTER, MOD_BEFORE_VAL, MOD_AFTER_VAL, MOD_DATE, MOD_REASON
            FROM prod_inst_log
            WHERE prod_inst_id = '207120377'
            ORDER BY AUD_DATE DESC



实例更新语句:

读取 excel 中实例对应的   脚本 语句即:

更新语句





### 2. 优化现有 异常数据修复 大模型生成sql提示词模板

请按照上面生成的fewshort 添加到，大模型调用提示词模板中

且 优化现有的 逻辑， 在调用大模型时  需要  把查询 业务数据，和查询日志数据  都放入 提示词中， 



