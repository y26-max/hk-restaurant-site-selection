import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import math
import json
from pathlib import Path
from datetime import datetime
import plotly.express as px
import folium
from streamlit_folium import st_folium

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "restaurant_site.db"

st.set_page_config(page_title="HK Restaurant Site Selection", page_icon="🍽️", layout="wide")

DISTRICTS = [
    "Central and Western", "Wan Chai", "Eastern", "Southern",
    "Yau Tsim Mong", "Sham Shui Po", "Kowloon City", "Wong Tai Sin",
    "Kwun Tong", "Kwai Tsing", "Tsuen Wan", "Tuen Mun",
    "Yuen Long", "North", "Tai Po", "Sha Tin", "Sai Kung", "Islands"
]
RESTAURANT_TYPES = ["Coffee Shop", "Chinese Restaurant", "Western Restaurant", "Fast Food"]

# Demonstration data only. Replace/import real data before making business decisions.
DEMO_DISTRICTS = [
    ("Central and Western", 22.2819, 114.1589, 240000, 42, 72000, 16000, 82),
    ("Wan Chai", 22.2770, 114.1722, 180000, 40, 65000, 14500, 90),
    ("Eastern", 22.2840, 114.2240, 560000, 44, 52000, 11000, 68),
    ("Southern", 22.2470, 114.1580, 270000, 44, 58000, 9000, 48),
    ("Yau Tsim Mong", 22.3193, 114.1694, 340000, 40, 48000, 19000, 95),
    ("Sham Shui Po", 22.3307, 114.1622, 430000, 43, 39000, 12500, 60),
    ("Kowloon City", 22.3282, 114.1916, 420000, 43, 51000, 13000, 64),
    ("Wong Tai Sin", 22.3420, 114.1930, 420000, 45, 43000, 10000, 54),
    ("Kwun Tong", 22.3129, 114.2250, 670000, 42, 47000, 15000, 72),
    ("Kwai Tsing", 22.3549, 114.1050, 510000, 43, 44000, 9500, 50),
    ("Tsuen Wan", 22.3707, 114.1130, 320000, 43, 50000, 11000, 58),
    ("Tuen Mun", 22.3910, 113.9770, 510000, 44, 42000, 8500, 42),
    ("Yuen Long", 22.4456, 114.0220, 660000, 42, 46000, 9000, 47),
    ("North", 22.5000, 114.1300, 310000, 43, 45000, 7500, 36),
    ("Tai Po", 22.4500, 114.1650, 300000, 43, 52000, 8500, 40),
    ("Sha Tin", 22.3810, 114.1880, 690000, 42, 55000, 12000, 62),
    ("Sai Kung", 22.3830, 114.2700, 130000, 42, 65000, 10000, 35),
    ("Islands", 22.2600, 113.9500, 180000, 42, 50000, 7000, 30),
]

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects(
            project_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            restaurant_type TEXT NOT NULL,
            target_district TEXT,
            rental_budget REAL,
            min_area REAL,
            max_area REAL,
            target_customer TEXT,
            average_spending REAL DEFAULT 80,
            customers_per_day REAL DEFAULT 100,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS district_stats(
            district TEXT PRIMARY KEY,
            latitude REAL, longitude REAL, population INTEGER,
            median_age REAL, median_household_income REAL,
            indicative_rent_sqft REAL, competitor_count INTEGER,
            data_status TEXT DEFAULT 'DEMO - replace with official data'
        );
        CREATE TABLE IF NOT EXISTS locations(
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            district TEXT NOT NULL,
            address TEXT,
            latitude REAL, longitude REAL,
            area_sqft REAL, monthly_rent REAL,
            source TEXT DEFAULT 'User upload',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS restaurants(
            restaurant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, restaurant_type TEXT, district TEXT,
            address TEXT, latitude REAL, longitude REAL,
            source TEXT DEFAULT 'User upload'
        );
        CREATE TABLE IF NOT EXISTS uploads(
            upload_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, filename TEXT, imported_at TEXT,
            rows_imported INTEGER, status TEXT
        );
        CREATE TABLE IF NOT EXISTS scores(
            score_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER, district TEXT,
            demographic_score REAL, transport_score REAL,
            competition_score REAL, rental_score REAL,
            facilities_score REAL, total_score REAL,
            calculated_at TEXT
        );
        """)
        count = c.execute("SELECT COUNT(*) FROM district_stats").fetchone()[0]
        if count == 0:
            c.executemany("""INSERT INTO district_stats
                (district,latitude,longitude,population,median_age,median_household_income,indicative_rent_sqft,competitor_count)
                VALUES (?,?,?,?,?,?,?,?)""", DEMO_DISTRICTS)

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def register(username, email, password):
    try:
        with connect() as c:
            c.execute("INSERT INTO users(username,email,password_hash,created_at) VALUES(?,?,?,?)",
                      (username, email, hash_password(password), datetime.now().isoformat(timespec="seconds")))
        return True
    except sqlite3.IntegrityError:
        return False

def login(username, password):
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                        (username, hash_password(password))).fetchone()
    return dict(row) if row else None

def get_districts():
    with connect() as c:
        return pd.read_sql_query("SELECT * FROM district_stats ORDER BY district", c)

def save_project(user_id, values):
    with connect() as c:
        c.execute("""INSERT INTO projects(user_id,project_name,restaurant_type,target_district,rental_budget,
                  min_area,max_area,target_customer,average_spending,customers_per_day,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                  (user_id, values["name"], values["type"], values["district"], values["budget"],
                   values["min_area"], values["max_area"], values["customer"], values["spend"],
                   values["customers"], datetime.now().isoformat(timespec="seconds")))

def get_projects(user_id):
    with connect() as c:
        return pd.read_sql_query("SELECT * FROM projects WHERE user_id=? ORDER BY project_id DESC", c, params=(user_id,))

def save_locations(df, user_id, filename):
    required = {"district", "address", "latitude", "longitude", "area_sqft", "monthly_rent"}
    if not required.issubset(set(df.columns)):
        raise ValueError("CSV/Excel 必须包含字段：" + ", ".join(sorted(required)))
    df = df.copy()
    for col in ["latitude","longitude","area_sqft","monthly_rent"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["latitude","longitude","area_sqft","monthly_rent"])
    df["district"] = df["district"].astype(str)
    df["address"] = df["address"].fillna("").astype(str)
    with connect() as c:
        c.executemany("""INSERT INTO locations(district,address,latitude,longitude,area_sqft,monthly_rent,source,created_at)
                         VALUES(?,?,?,?,?,?,?,?)""",
                      [(r.district,r.address,float(r.latitude),float(r.longitude),float(r.area_sqft),
                        float(r.monthly_rent),filename,datetime.now().isoformat(timespec="seconds"))
                       for r in df.itertuples()])
        c.execute("INSERT INTO uploads(user_id,filename,imported_at,rows_imported,status) VALUES(?,?,?,?,?)",
                  (user_id, filename, datetime.now().isoformat(timespec="seconds"), len(df), "Imported"))
    return len(df)

def haversine_km(lat1, lon1, lat2, lon2):
    rad = math.pi / 180
    dlat, dlon = (lat2-lat1)*rad, (lon2-lon1)*rad
    a = math.sin(dlat/2)**2 + math.cos(lat1*rad)*math.cos(lat2*rad)*math.sin(dlon/2)**2
    return 6371 * 2 * math.asin(math.sqrt(a))

def minmax(series, higher=True):
    s = pd.to_numeric(series, errors="coerce")
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series([50.0]*len(s), index=s.index)
    out = (s-lo)/(hi-lo)*100
    return out if higher else 100-out

def calculate_scores(project, districts, weights):
    d = districts.copy()
    d["demographic_score"] = minmax(d["population"] * 0.55 + d["median_household_income"] * 0.45)
    d["transport_score"] = minmax(d["transport_proxy"])
    d["competition_score"] = minmax(d["competitor_count"], higher=False)
    d["rental_score"] = minmax(d["indicative_rent_sqft"], higher=False)
    d["facilities_score"] = minmax(d["facilities_proxy"])
    d["total_score"] = (
        d["demographic_score"]*weights["人口潜力"] +
        d["transport_score"]*weights["交通便利"] +
        d["competition_score"]*weights["竞争环境"] +
        d["rental_score"]*weights["租金成本"] +
        d["facilities_score"]*weights["周边设施"]
    ) / 100
    if project["target_district"] != "All Hong Kong":
        d = d[d["district"] == project["target_district"]]
    if project["rental_budget"] and project["rental_budget"] > 0:
        # This is an indicative district-level proxy, not a property-level affordability test.
        d["budget_note"] = "地区租金指标仅供初筛；请查看具体商铺租盘"
    return d.sort_values("total_score", ascending=False).reset_index(drop=True)

init_db()
if "user" not in st.session_state:
    st.session_state.user = None

st.title("🍽️ Hong Kong Restaurant Site Selection")
st.caption("香港餐饮智能选址平台 · MVP 原型")

if not st.session_state.user:
    tab1, tab2 = st.tabs(["登录 Login", "注册 Register"])
    with tab1:
        with st.form("login"):
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录")
            if submitted:
                user = login(u.strip(), p)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("用户名或密码不正确。")
    with tab2:
        with st.form("register"):
            nu = st.text_input("用户名", key="reg_u")
            em = st.text_input("邮箱", key="reg_e")
            npw = st.text_input("密码", type="password", key="reg_p")
            npw2 = st.text_input("确认密码", type="password", key="reg_p2")
            reg = st.form_submit_button("创建账号")
            if reg:
                if not nu.strip() or not npw:
                    st.error("用户名和密码不能为空。")
                elif npw != npw2:
                    st.error("两次输入的密码不一致。")
                elif register(nu.strip(), em.strip(), npw):
                    st.success("注册成功，请切换到登录页面。")
                else:
                    st.error("用户名已存在。")
    st.info("首次使用请先注册。此 MVP 使用本地 SQLite；正式上线前需要升级密码哈希、会话安全和权限控制。")
    st.stop()

user = st.session_state.user
with st.sidebar:
    st.write(f"👤 {user['username']}")
    if st.button("退出登录"):
        st.session_state.user = None
        st.rerun()
    page = st.radio("导航 Navigation", [
        "Dashboard", "Create Project", "Explore & Map", "Demographic Analysis",
        "Competitor Analysis", "Rental Analysis", "Location Recommendation",
        "Financial Estimation", "Upload Data", "Data Sources & Notes"
    ])

projects = get_projects(user["user_id"])
districts = get_districts()

if page == "Dashboard":
    st.header("Dashboard")
    a,b,c,d = st.columns(4)
    a.metric("我的项目", len(projects))
    with connect() as conn:
        uploaded = conn.execute("SELECT COUNT(*) FROM uploads WHERE user_id=?", (user["user_id"],)).fetchone()[0]
        saved = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    b.metric("上传批次", uploaded)
    c.metric("候选商铺记录", saved)
    d.metric("香港地区", 18)
    st.subheader("我的选址项目")
    if projects.empty:
        st.info("你还没有项目。请先进入 Create Project 创建一个餐饮选址项目。")
    else:
        st.dataframe(projects[["project_id","project_name","restaurant_type","target_district","rental_budget","created_at"]],
                     use_container_width=True, hide_index=True)
    st.subheader("地区人口概览（演示数据）")
    fig = px.bar(districts.sort_values("population", ascending=False), x="district", y="population",
                 title="各区人口示意比较", labels={"district":"地区","population":"人口"})
    st.plotly_chart(fig, use_container_width=True)

elif page == "Create Project":
    st.header("Create a Restaurant Project")
    with st.form("new_project"):
        name = st.text_input("项目名称", "我的香港咖啡店")
        rtype = st.selectbox("餐饮类型", RESTAURANT_TYPES)
        district = st.selectbox("目标地区", ["All Hong Kong"] + DISTRICTS)
        budget = st.number_input("每月租金预算（HKD）", min_value=0.0, value=30000.0, step=1000.0)
        c1,c2 = st.columns(2)
        min_area = c1.number_input("最小面积（平方尺）", min_value=0.0, value=300.0)
        max_area = c2.number_input("最大面积（平方尺）", min_value=0.0, value=1000.0)
        customer = st.selectbox("目标顾客", ["Students","Office Workers","Residents and Families","Tourists","General"])
        c3,c4 = st.columns(2)
        spend = c3.number_input("预计人均消费（HKD）", min_value=1.0, value=80.0)
        customers = c4.number_input("预计每日顾客人数", min_value=1.0, value=100.0)
        ok = st.form_submit_button("创建项目")
        if ok:
            if max_area and min_area > max_area:
                st.error("最大面积必须大于或等于最小面积。")
            else:
                save_project(user["user_id"], {"name":name,"type":rtype,"district":district,"budget":budget,
                    "min_area":min_area,"max_area":max_area,"customer":customer,"spend":spend,"customers":customers})
                st.success("项目创建成功！")
                st.rerun()

elif page == "Explore & Map":
    st.header("Explore Hong Kong")
    st.caption("地图上的地区中心点是示意位置；上传商铺记录后会显示实际候选商铺坐标。")
    loc_filter = st.multiselect("筛选地区", DISTRICTS, default=["Yau Tsim Mong","Wan Chai","Central and Western"])
    m = folium.Map(location=[22.32,114.17], zoom_start=11, tiles="OpenStreetMap")
    for r in districts[districts.district.isin(loc_filter)].itertuples():
        folium.CircleMarker([r.latitude,r.longitude], radius=8, popup=f"{r.district}（示意点）",
                            color="#2563eb", fill=True).add_to(m)
    with connect() as conn:
        locs = pd.read_sql_query("SELECT * FROM locations", conn)
    if not locs.empty:
        for r in locs.itertuples():
            folium.Marker([r.latitude,r.longitude], popup=f"{r.address}<br>HK${r.monthly_rent:,.0f}/月",
                          tooltip=r.district, icon=folium.Icon(color="green",icon="home")).add_to(m)
    st_folium(m, use_container_width=True, height=550)
    if not locs.empty:
        st.subheader("已导入的候选商铺")
        st.dataframe(locs, use_container_width=True, hide_index=True)

elif page == "Demographic Analysis":
    st.header("Demographic Analysis")
    st.warning("当前内置人口数据为演示数据，不可用于真实商业决策。请通过官方数据导入流程替换。")
    metric = st.selectbox("分析指标", ["population","median_age","median_household_income"])
    labels = {"population":"人口","median_age":"年龄中位数","median_household_income":"家庭收入中位数"}
    fig = px.bar(districts.sort_values(metric, ascending=False), x="district", y=metric,
                 title=f"各区{labels[metric]}", labels={"district":"地区",metric:labels[metric]})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(districts[["district","population","median_age","median_household_income","data_status"]],
                 use_container_width=True, hide_index=True)

elif page == "Competitor Analysis":
    st.header("Competitor Analysis")
    st.caption("竞争对手数据需要从许可数据源或用户上传文件导入。")
    with connect() as conn:
        rests = pd.read_sql_query("SELECT * FROM restaurants", conn)
    if rests.empty:
        st.info("目前没有导入餐厅记录。请在 Upload Data 上传 restaurants CSV。")
    else:
        types = ["All"] + sorted(rests.restaurant_type.dropna().unique().tolist())
        typ = st.selectbox("餐厅类型", types)
        shown = rests if typ == "All" else rests[rests.restaurant_type == typ]
        st.metric("餐厅记录数", len(shown))
        fig = px.scatter_mapbox(shown, lat="latitude", lon="longitude", color="restaurant_type",
                                hover_name="name", zoom=10, height=500, mapbox_style="open-street-map")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(shown, use_container_width=True, hide_index=True)

elif page == "Rental Analysis":
    st.header("Rental Analysis")
    with connect() as conn:
        locs = pd.read_sql_query("SELECT * FROM locations", conn)
    if locs.empty:
        st.info("尚无商铺租金数据。请在 Upload Data 上传 locations CSV。")
    else:
        locs["rent_per_sqft"] = locs.monthly_rent / locs.area_sqft
        st.metric("已导入商铺", len(locs))
        st.metric("平均每平方尺月租", f"HK${locs.rent_per_sqft.mean():,.2f}")
        fig = px.box(locs, x="district", y="rent_per_sqft", points="all",
                     labels={"district":"地区","rent_per_sqft":"每平方尺月租（HKD）"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(locs, use_container_width=True, hide_index=True)

elif page == "Location Recommendation":
    st.header("Location Recommendation")
    if projects.empty:
        st.warning("请先创建项目。")
    else:
        pmap = {f"{r.project_id} — {r.project_name}": r for r in projects.itertuples()}
        selected = st.selectbox("选择项目", list(pmap.keys()))
        p = pmap[selected]
        st.caption(f"餐饮类型：{p.restaurant_type} · 目标地区：{p.target_district}")
        st.subheader("调整评分权重")
        cols = st.columns(5)
        defaults = [25,20,20,20,15]
        names = ["人口潜力","交通便利","竞争环境","租金成本","周边设施"]
        weights = {}
        for i,n in enumerate(names):
            weights[n] = cols[i].number_input(n, min_value=0, max_value=100, value=defaults[i], step=5)
        totalw = sum(weights.values())
        if totalw == 0:
            st.error("权重总和不能为 0。")
        else:
            weights = {k:v/totalw*100 for k,v in weights.items()}
            d = districts.copy()
            # These proxies are placeholders until real transport/facility datasets are loaded.
            d["transport_proxy"] = [82,90,65,45,95,58,62,52,72,50,58,42,47,36,40,62,35,30]
            d["facilities_proxy"] = [85,90,70,55,95,60,65,55,78,50,60,42,48,38,45,68,40,35]
            scored = calculate_scores(p, d, weights)
            st.subheader("推荐地区排名")
            view = scored[["district","total_score","demographic_score","transport_score","competition_score","rental_score","facilities_score"]].copy()
            view.columns = ["地区","综合评分","人口","交通","竞争","租金","设施"]
            view["综合评分"] = view["综合评分"].round(1)
            st.dataframe(view, use_container_width=True, hide_index=True)
            best = scored.iloc[0]
            st.success(f"当前模型排名第一：{best['district']}，综合评分 {best['total_score']:.1f}/100。此结果基于演示数据和示意指标。")
            fig = px.bar(scored.head(10), x="district", y="total_score", title="Top 10 地区综合评分",
                         labels={"district":"地区","total_score":"综合评分"})
            st.plotly_chart(fig, use_container_width=True)
            if st.button("保存本次评分结果"):
                with connect() as conn:
                    conn.execute("DELETE FROM scores WHERE project_id=?", (p.project_id,))
                    conn.executemany("""INSERT INTO scores(project_id,district,demographic_score,transport_score,
                        competition_score,rental_score,facilities_score,total_score,calculated_at)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        [(p.project_id,r.district,r.demographic_score,r.transport_score,r.competition_score,
                          r.rental_score,r.facilities_score,r.total_score,datetime.now().isoformat(timespec="seconds"))
                         for r in scored.itertuples()])
                st.success("评分结果已保存。")

elif page == "Financial Estimation":
    st.header("Financial Estimation")
    if projects.empty:
        st.info("请先创建项目。")
    else:
        pmap = {f"{r.project_id} — {r.project_name}": r for r in projects.itertuples()}
        p = pmap[st.selectbox("选择项目", list(pmap.keys()))]
        rent = st.number_input("预计每月租金（HKD）", min_value=0.0, value=float(p.rental_budget or 30000))
        staff = st.number_input("每月员工成本（HKD）", min_value=0.0, value=40000.0)
        other = st.number_input("其他固定成本（HKD）", min_value=0.0, value=15000.0)
        variable_pct = st.slider("食材等变动成本占营业额比例", 0, 90, 35)
        days = st.number_input("每月营业天数", min_value=1, max_value=31, value=30)
        revenue = p.customers_per_day * p.average_spending * days
        fixed = rent + staff + other
        contribution = p.average_spending * (1-variable_pct/100)
        breakeven = fixed / contribution if contribution > 0 else 0
        x,y,z = st.columns(3)
        x.metric("预计月营业额", f"HK${revenue:,.0f}")
        y.metric("预计固定成本", f"HK${fixed:,.0f}")
        z.metric("每日盈亏平衡顾客数", f"{breakeven:,.1f}")
        st.caption("仅为用户输入假设下的情景估算，不构成收入或利润保证。")

elif page == "Upload Data":
    st.header("Upload Data")
    st.markdown("""
    支持两类 CSV 上传：
    - **locations.csv**：`district, address, latitude, longitude, area_sqft, monthly_rent`
    - **restaurants.csv**：`name, restaurant_type, district, address, latitude, longitude`

    Excel 文件可先另存为 CSV。导入前请确认坐标为香港经纬度（WGS84）。
    """)
    kind = st.radio("数据类型", ["候选商铺 locations", "餐厅 restaurants"], horizontal=True)
    uploaded_file = st.file_uploader("选择 CSV 文件", type=["csv"])
    if uploaded_file:
        try:
            data = pd.read_csv(uploaded_file)
            st.subheader("数据预览")
            st.dataframe(data.head(20), use_container_width=True)
            if st.button("确认导入"):
                if kind == "候选商铺 locations":
                    n = save_locations(data, user["user_id"], uploaded_file.name)
                else:
                    required = {"name","restaurant_type","district","address","latitude","longitude"}
                    if not required.issubset(data.columns):
                        raise ValueError("餐厅 CSV 必须包含：" + ", ".join(sorted(required)))
                    for col in ["latitude","longitude"]:
                        data[col] = pd.to_numeric(data[col], errors="coerce")
                    data = data.dropna(subset=["latitude","longitude"])
                    with connect() as conn:
                        conn.executemany("""INSERT INTO restaurants(name,restaurant_type,district,address,latitude,longitude,source)
                            VALUES(?,?,?,?,?,?,?)""",
                            [(str(r.name),str(r.restaurant_type),str(r.district),str(r.address),float(r.latitude),
                              float(r.longitude),uploaded_file.name) for r in data.itertuples()])
                    n = len(data)
                st.success(f"成功导入 {n} 条记录。")
        except Exception as e:
            st.error(f"导入失败：{e}")

elif page == "Data Sources & Notes":
    st.header("Data Sources & Notes")
    st.markdown("""
    ### 建议接入的香港数据来源
    1. **香港政府统计处 C&SD**：人口、年龄、家庭收入等统计数据。  
       https://www.censtatd.gov.hk/
    2. **食物环境卫生署 FEHD**：持牌食肆及相关公开资料。  
       https://www.fehd.gov.hk/
    3. **香港地理空间数据平台 CSDI**：地理空间、设施及交通相关数据。  
       https://portal.csdi.gov.hk/
    4. **data.gov.hk**：政府开放数据目录。  
       https://data.gov.hk/

    ### 关于自动获取数据
    本版本已提供数据导入和分析框架，但没有伪装成已连接实时官方 API。不同政府数据集的 API 地址、格式、许可和更新频率不同，接入前需要逐个核实。下一步可为 C&SD、FEHD、CSDI 分别编写专用 connector。

    ### 重要限制
    - 当前内置地区统计、竞争数量、交通和设施指标均为演示/代理数据。
    - 地区中心点不代表具体商铺位置。
    - FEHD 牌照类别不等同于咖啡店、中餐、西餐等菜系分类。
    - 人口和租金指标不能单独证明商业成功。
    - 正式部署前需加强密码存储、权限控制、数据授权、日志、备份和隐私保护。
    """)
