# 香港餐饮智能选址平台（MVP）

## 1. 环境要求
- Python 3.10 或更新版本
- VS Code（可选）

## 2. 安装和运行

在 VS Code 终端进入本项目文件夹：

```bash
python -m venv .venv
```

Windows PowerShell 激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
pip install -r requirements.txt
```

启动网站：

```bash
streamlit run app.py
```

浏览器会打开本地网站。首次使用请先注册账号。

## 3. 上传数据格式

### 候选商铺 CSV
必须包含以下列：

```csv
district,address,latitude,longitude,area_sqft,monthly_rent
Yau Tsim Mong,Example Road 1,22.3193,114.1694,500,30000
Wan Chai,Example Road 2,22.2770,114.1722,650,42000
```

### 餐厅 CSV
必须包含以下列：

```csv
name,restaurant_type,district,address,latitude,longitude
Example Cafe,Coffee Shop,Yau Tsim Mong,Example Road 1,22.3193,114.1694
```

坐标使用 WGS84 经纬度。请只上传你有权使用的数据。

## 4. 当前版本已实现
- 用户注册、登录和退出（本地原型）
- 创建选址项目
- 香港 18 区演示数据
- 地图展示地区示意点及上传商铺
- 人口分析图表
- 餐厅数据导入和竞争数据展示
- 商铺租金分析
- 可调整权重的地区评分
- 财务情景估算
- SQLite 数据保存

## 5. 重要说明
内置人口、收入、竞争数量、交通和设施指标是演示数据/代理数据，不是实时官方数据。当前版本没有声称已经接通政府实时 API。请在商业使用前接入并核实 C&SD、FEHD、CSDI 等数据集，保留来源、采集时间、许可和数据质量信息。

此版本是本地 MVP 原型，不适合直接作为公开生产服务。正式上线前应改用安全密码哈希（如 Argon2/bcrypt）、严格用户数据隔离、HTTPS、备份、日志和权限控制。
