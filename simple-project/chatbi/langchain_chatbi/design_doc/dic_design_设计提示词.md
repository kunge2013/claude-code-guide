### 你是一个chatbi设计高手
### 基于当前项目，进行设计，并解耦改造

### 需求

#### 1.用户数据关联信息描述时， 可以找到相关的编码进行转换， 然后根据转换后的值，进行过滤数据

''
CREATE TABLE `prod_info` (
  `prod_id` bigint DEFAULT NULL COMMENT '产品ID',
  `prod_name` varchar(100) DEFAULT NULL COMMENT '产品名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='产品信息表'
''


''
CREATE TABLE `special_settlement_rule_config` (
  `ID` bigint NOT NULL AUTO_INCREMENT COMMENT '系统生成的唯一标识符',
  `SPECIAL_RULE_ID` varchar(64) NOT NULL COMMENT '用于关联一组配置',
  `PROD_ID` varchar(64) NOT NULL COMMENT '产品ID',
  `ACCT_ITEM_TYPE` varchar(64) NOT NULL COMMENT '账目项编码',
  `EXT_PROD_INST_ID` varchar(64) NOT NULL COMMENT '外部实例ID',
  `SETTLE_TYPE` varchar(32) NOT NULL COMMENT '结算类型（40001002：按比例）',
  `SETTLE_VAL` varchar(16) NOT NULL COMMENT '结算比例（0-1），当结算类型为按比例时必填',
  `SETTLE_OBJ_ID` varchar(128) NOT NULL COMMENT '分摊对象ID',
  `OBJ_ID` varchar(128) DEFAULT NULL COMMENT '结算对象ID（省公司、特定单位等）',
  `OBJ_NAME` varchar(32) DEFAULT NULL COMMENT '结算对象名称',
  `SOURCE_SQL` longtext COMMENT '存储结算规则相关的属性查询SQL，用于动态获取结算参数',
  `STATUS` varchar(5) NOT NULL DEFAULT '1000' COMMENT '状态（1000:启用，1001:禁用）',
  `CREATE_DATE` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `CREATE_BY` varchar(64) DEFAULT NULL COMMENT '创建人',
  `UPDATE_DATE` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  `UPDATE_BY` varchar(64) DEFAULT NULL COMMENT '修改人',
  `REMARK` varchar(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`ID`),
  KEY `IDX_SPECIAL_RULE_ID` (`SPECIAL_RULE_ID`),
  KEY `IDX_EXT_PROD_INST_ID` (`EXT_PROD_INST_ID`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='特殊结算规则配置表'
''

special_settlement_rule_config.prod_id = prod_info.prod_id

prod_info 数据如下
PROD    PROD_NAME
1001	云总机
1002	工作号

当我问  云总机 有哪些配置时候 需要你查询 special_settlement_rule_config 带上 prod_id = 1001 的条件

有没有一个合理的设计， 可以通用转换后查询 special_settlement_rule_config数据

