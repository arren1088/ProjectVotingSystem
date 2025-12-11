from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, make_response
import os
import io
import sqlite3
import pandas as pd
from datetime import datetime
import json
import logging
app = Flask(__name__)
app.secret_key = os.urandom(24)

logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(BASE_DIR, "data")):
    os.makedirs(os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(BASE_DIR, "data", "database.db")
GROUPS_FILE = os.path.join(BASE_DIR, "data", "groups.json")

def login_required(route_func):
    def wrapper(*args, **kwargs):
        if not session.get("student_id"):
            logging.warning(f"Unauthorized access attempt to {request.path}")
            return redirect(url_for("index", message="請先登入"))
        return route_func(*args, **kwargs)
    wrapper.__name__ = route_func.__name__
    return wrapper

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    student_name TEXT NOT NULL,
                    student_class TEXT,
                    has_voted INTEGER DEFAULT 0
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS votes (
                    student_id TEXT,
                    group_id TEXT,
                    vote_time TEXT,
                    PRIMARY KEY (student_id, group_id)
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    feedback TEXT NOT NULL,
                    feedback_date TEXT,
                    feedback_time TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    teacher TEXT,
                    lab_number TEXT
                )
            ''')
            conn.commit()
            logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Failed to initialize database: {e}")
        raise

def load_groups():
    try:
        if os.path.exists(GROUPS_FILE):
            with open(GROUPS_FILE, "r", encoding="utf-8") as f:
                groups = json.load(f)
                logging.info(f"Loaded {len(groups)} groups from groups.json")
                return groups
        logging.warning("Groups file not found.")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding groups.json: {e}")
        return []
    except Exception as e:
        logging.error(f"Error loading groups.json: {e}")
        return []

def sync_groups():
    try:
        groups = load_groups()
        if not groups:
            logging.warning("No groups found in groups.json. Skipping sync.")
            return

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            for group in groups:
                c.execute('''
                    INSERT OR REPLACE INTO groups (id, name, teacher, lab_number)
                    VALUES (?, ?, ?, ?)
                ''', (group['id'], group['name'], group.get('teacher', ''), group.get('lab_number', '')))
            conn.commit()
            logging.info(f"Synchronized {len(groups)} groups to database.")
    except sqlite3.Error as e:
        logging.error(f"Error syncing groups to database: {e}")

def migrate_feedbacks_table():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedbacks'")
            if not c.fetchone():
                logging.warning("Feedbacks table does not exist. Skipping migration.")
                return
            c.execute("PRAGMA table_info(feedbacks)")
            columns = [col[1] for col in c.fetchall()]
            if 'feedback_date' not in columns:
                c.execute("ALTER TABLE feedbacks ADD COLUMN feedback_date TEXT")
                logging.info("Added feedback_date column to feedbacks table.")
            if 'feedback_time' not in columns:
                c.execute("ALTER TABLE feedbacks ADD COLUMN feedback_time TEXT")
                logging.info("Added feedback_time column to feedbacks table.")
            c.execute('''
                UPDATE feedbacks
                SET feedback_date = COALESCE(feedback_date, DATE(timestamp)),
                    feedback_time = COALESCE(feedback_time, TIME(timestamp))
                WHERE feedback_date IS NULL OR feedback_time IS NULL
            ''')
            conn.commit()
            logging.info("Feedbacks table migrated successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error migrating feedbacks table: {e}")

def update_feedbacks_table():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedbacks'")
            if not c.fetchone():
                logging.warning("Feedbacks table does not exist. Reinitializing database.")
                init_db()
            c.execute("PRAGMA table_info(feedbacks)")
            columns = [column[1] for column in c.fetchall()]
            if 'group_id' not in columns:
                c.execute("ALTER TABLE feedbacks ADD COLUMN group_id TEXT")
                logging.info("Added group_id column to feedbacks table.")
            conn.commit()
    except sqlite3.OperationalError as e:
        logging.error(f"Error updating feedbacks table: {e}")

def check_database():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in c.fetchall()]
            logging.info(f"Tables in database: {tables}")
            if 'feedbacks' in tables:
                c.execute("PRAGMA table_info(feedbacks)")
                columns = [column[1] for column in c.fetchall()]
                logging.info(f"Columns in feedbacks table: {columns}")
                c.execute("SELECT COUNT(*) FROM feedbacks")
                count = c.fetchone()[0]
                logging.info(f"Number of feedback records: {count}")
            if 'votes' in tables:
                c.execute("SELECT COUNT(*) FROM votes")
                count = c.fetchone()[0]
                logging.info(f"Number of vote records: {count}")
            if 'groups' in tables:
                c.execute("SELECT COUNT(*) FROM groups")
                count = c.fetchone()[0]
                logging.info(f"Number of group records: {count}")
    except sqlite3.Error as e:
        logging.error(f"Error checking database: {e}")

init_db()
sync_groups()
migrate_feedbacks_table()
update_feedbacks_table()
check_database()

def get_votes_by_student(student_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT group_id, vote_time FROM votes WHERE student_id = ?", (student_id,))
            votes = [{"group_id": row[0], "vote_time": row[1]} for row in c.fetchall()]
        return votes
    except sqlite3.Error as e:
        logging.error(f"Error fetching votes for student {student_id}: {e}")
        return []

def validate_group_id(group_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM groups WHERE id = ?", (group_id,))
            return c.fetchone() is not None
    except sqlite3.Error as e:
        logging.error(f"Error validating group_id {group_id}: {e}")
        return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    student_id = request.form.get("student_id")
    student_name = request.form.get("student_name")
    student_class = request.form.get("student_class")

    if not student_id or len(student_id) != 9 or not student_id.isdigit():
        return render_template("index.html", message="請輸入正確學號。")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT has_voted FROM students WHERE student_id = ?", (student_id,))
            row = c.fetchone()

            if row:
                if row[0] == 1:
                    return render_template("index.html", message="此學號已投票，不得重複投票。")
                else:
                    session["student_id"] = student_id
                    session["votes"] = get_votes_by_student(student_id)
                    return redirect(url_for("vote_page"))

            c.execute("INSERT INTO students (student_id, student_name, student_class) VALUES (?, ?, ?)",
                      (student_id, student_name, student_class))
            conn.commit()
            logging.info(f"Registered student: {student_id}")
    except sqlite3.Error as e:
        logging.error(f"Error registering student {student_id}: {e}")
        return render_template("index.html", message="註冊失敗，請稍後再試。")

    session["student_id"] = student_id
    session["votes"] = []
    return redirect(url_for("vote_page"))

@app.route("/vote")
@login_required
def vote_page():
    student_id = session.get("student_id")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT has_voted FROM students WHERE student_id = ?", (student_id,))
            row = c.fetchone()
    except sqlite3.Error as e:
        logging.error(f"Error checking vote status for student {student_id}: {e}")
        return redirect(url_for("index", message="無法載入投票頁面，請重新登入"))

    if not row:
        return redirect(url_for("index", message="學生資料不存在，請重新登入"))

    if row[0] == 1:
        return redirect(url_for("succeed"))

    votes = get_votes_by_student(student_id)
    session["votes"] = votes
    groups = load_groups()
    return render_template("vote.html", groups=groups)

@app.route("/api/vote", methods=["POST"])
@login_required
def vote():
    student_id = session.get("student_id")
    data = request.get_json()
    group_id = data.get("group_id")

    if not group_id:
        return jsonify({"success": False, "message": "缺少組別 ID"}), 400

    votes = get_votes_by_student(student_id)
    if group_id in [v["group_id"] for v in votes]:
        return jsonify({"success": False, "message": "您已經投過此組別！"}), 403
    if len(votes) >= 3:
        return jsonify({"success": False, "message": "您已經投過三票了！"}), 403

    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            vote_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO votes (student_id, group_id, vote_time) VALUES (?, ?, ?)",
                      (student_id, group_id, vote_time))
            conn.commit()
            logging.info(f"Vote recorded: student={student_id}, group={group_id}")
    except sqlite3.Error as e:
        logging.error(f"Error recording vote for student {student_id}: {e}")
        return jsonify({"success": False, "message": "投票失敗"}), 500

    votes.append({"group_id": group_id, "vote_time": vote_time})
    session["votes"] = votes
    return jsonify({"success": True})

@app.route("/api/vote/confirm", methods=["POST"])
@login_required
def confirm_vote():
    student_id = session.get("student_id")
    data = request.get_json()
    selected_votes = data.get("selected_votes", [])

    if len(selected_votes) != 3:
        return jsonify({"success": False, "message": "必須選擇三組"}), 400

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM votes WHERE student_id = ?", (student_id,))
            if cursor.fetchone()[0] > 0:
                return jsonify({"success": False, "message": "你已經投過票了"}), 400

            vote_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for group_id in selected_votes:
                cursor.execute(
                    "INSERT INTO votes (student_id, group_id, vote_time) VALUES (?, ?, ?)",
                    (student_id, group_id, vote_time)
                )

            cursor.execute("UPDATE students SET has_voted = 1 WHERE student_id = ?", (student_id,))
            session["votes"] = [{"group_id": group_id, "vote_time": vote_time} for group_id in selected_votes]
            conn.commit()
            logging.info(f"Confirmed votes for student {student_id}")
            return jsonify({"success": True})
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error confirming votes for student {student_id}: {e}")
        return jsonify({"success": False, "message": "寫入失敗"}), 500

@app.route("/api/toggle_vote", methods=["POST"])
@login_required
def toggle_vote():
    student_id = session.get("student_id")
    data = request.get_json()
    group_id = data.get("group_id")

    if not group_id:
        return jsonify({"success": False, "message": "缺少組別 ID"}), 400

    votes = get_votes_by_student(student_id)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            if group_id in [v["group_id"] for v in votes]:
                c.execute("DELETE FROM votes WHERE student_id = ? AND group_id = ?", (student_id, group_id))
                message = "已取消投票"
                voted = False
                logging.info(f"Vote cancelled: student={student_id}, group={group_id}")
            else:
                if len(votes) >= 3:
                    return jsonify({"success": False, "message": "最多只能投三票"}), 403
                vote_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO votes (student_id, group_id, vote_time) VALUES (?, ?, ?)",
                          (student_id, group_id, vote_time))
                message = "投票成功"
                voted = True
                logging.info(f"Vote recorded: student={student_id}, group={group_id}")
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error toggling vote for student {student_id}: {e}")
        return jsonify({"success": False, "message": "投票操作失敗"}), 500

    session["votes"] = get_votes_by_student(student_id)
    return jsonify({"success": True, "message": message, "voted": voted, "vote_count": len(session['votes'])})

@app.route("/succeed")
@login_required
def succeed():
    session.clear()
    response = make_response(render_template("succeed.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/feedbacks")
@login_required
def feedbacks():
    groups = load_groups()
    return render_template("feedbacks.html", groups=groups)

@app.route("/api/feedback", methods=["POST"])
@login_required
def submit_feedback():
    student_id = session.get("student_id")
    feedback = request.form.get("feedback", "").strip()
    group_id = request.form.get("group_id")
    feedback_date = request.form.get("feedback_date")
    feedback_time = request.form.get("feedback_time")

    logging.info(f"Received feedback: student={student_id}, group={group_id}, "
                 f"feedback={feedback}, date={feedback_date}, time={feedback_time}")

    if not feedback or not group_id or not feedback_date or not feedback_time:
        logging.warning("Incomplete feedback data received.")
        return jsonify({"success": False, "message": "請選擇組別、填寫建議並選擇日期與時間"}), 400

    if not validate_group_id(group_id):
        logging.warning(f"Invalid group_id: {group_id}")
        return jsonify({"success": False, "message": "無效的組別 ID"}), 400

    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO feedbacks (student_id, group_id, feedback, feedback_date, feedback_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, group_id, feedback, feedback_date, feedback_time))
            conn.commit()
            logging.info(f"Feedback inserted: student={student_id}, group={group_id}")
    except sqlite3.Error as e:
        logging.error(f"Error inserting feedback for student {student_id}: {e}")
        return jsonify({"success": False, "message": "提交回饋失敗"}), 500

    return redirect(url_for("succeed"))

@app.route("/api/feedback/batch", methods=["POST"])
@login_required
def batch_feedback():
    student_id = session.get("student_id")
    feedback_data = request.form.get("data")
    if not feedback_data:
        logging.info(f"No feedback data received for student {student_id}. Allowing empty submission.")
        return jsonify({"success": True})

    try:
        feedbacks = json.loads(feedback_data)
        logging.info(f"Received batch feedback: student={student_id}, count={len(feedbacks)}")
    except json.JSONDecodeError:
        logging.error("Invalid JSON in batch feedback data.")
        return jsonify({"success": False, "message": "回饋資料格式錯誤"}), 400

    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            for feedback in feedbacks:
                group_id = feedback["groupId"]
                if not validate_group_id(group_id):
                    logging.warning(f"Invalid group_id in batch: {group_id}")
                    continue
                c.execute('''
                    INSERT INTO feedbacks (student_id, group_id, feedback, feedback_date, feedback_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (student_id, group_id, feedback["feedback"],
                      feedback["feedbackDate"], feedback["feedbackTime"]))
            conn.commit()
            logging.info(f"Batch feedback inserted: student={student_id}, count={len(feedbacks)}")
    except sqlite3.Error as e:
        logging.error(f"Error inserting batch feedback for student {student_id}: {e}")
        return jsonify({"success": False, "message": "批量提交回饋失敗"}), 500

    return jsonify({"success": True})

ADMIN_PASSWORD = "pucsim1114"

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            session.permanent = False
            return redirect(url_for("admin"))
        else:
            return render_template("admin_login.html", message="密碼錯誤")

    return render_template("admin_login.html")

def admin_required(route_func):
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return route_func(*args, **kwargs)
    wrapper.__name__ = route_func.__name__
    return wrapper

@app.route("/admin_logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT student_id, student_name, student_class FROM students")
            students_raw = c.fetchall()
            logging.info(f"Fetched {len(students_raw)} student records")

            student_votes = {}
            for student_id, name, student_class in students_raw:
                c.execute("SELECT group_id, vote_time FROM votes WHERE student_id = ?", (student_id,))
                group_votes = [{"group_id": row[0], "vote_time": row[1]} for row in c.fetchall()]
                student_votes[student_id] = {"name": name, "class": student_class or "未知班級", "votes": group_votes}

            c.execute("SELECT group_id, COUNT(*) FROM votes GROUP BY group_id")
            vote_counts = c.fetchall()
            logging.info(f"Fetched {len(vote_counts)} vote count records")
    except sqlite3.Error as e:
        logging.error(f"Error fetching admin data: {e}")
        return render_template("admin.html", students={}, vote_counts_data=[], message="無法載入資料")

    groups = load_groups()
    vote_counts_data = []
    for group_id, count in vote_counts:
        group_name = next((group['name'] for group in groups if group['id'] == group_id), '未知組別')
        vote_counts_data.append({"group_id": group_id, "group_name": group_name, "vote_count": count})
    vote_counts_data = sorted(vote_counts_data, key=lambda x: x['vote_count'], reverse=True)
    logging.info(f"Prepared {len(vote_counts_data)} vote count entries for display")

    return render_template("admin.html", students=student_votes, vote_counts_data=vote_counts_data)

@app.route("/admin/download_votes")
def download_votes():
    groups = load_groups()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT student_id, student_name, student_class FROM students")
            students_raw = c.fetchall()

            student_votes = []
            for student_id, name, student_class in students_raw:
                c.execute("SELECT group_id, vote_time FROM votes WHERE student_id = ?", (student_id,))
                group_votes = [{"group_id": row[0], "vote_time": row[1]} for row in c.fetchall()]
                for group_vote in group_votes:
                    group_name = next((group['name'] for group in groups if group['id'] == group_vote['group_id']), '未知組別')
                    student_votes.append({
                        "student_id": student_id,
                        "student_name": name,
                        "student_class": student_class or "未知班級",
                        "group_name": group_name,
                        "vote_time": group_vote['vote_time']
                    })
    except sqlite3.Error as e:
        logging.error(f"Error downloading votes: {e}")
        return jsonify({"success": False, "message": "無法下載投票資料"}), 500

    df = pd.DataFrame(student_votes)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Votes")
    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="投票結果.xlsx")

@app.route("/admin/download_student_votes")
def download_student_votes():
    groups = load_groups()  # groups.json 的資料

    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()

            # 取得 votes 表所有 group_id
            c.execute("SELECT group_id FROM votes")
            all_votes = [row[0] for row in c.fetchall()]

            # 各組票數統計
            group_stats = []
            for g in groups:
                group_id = g["id"]
                group_name = g["name"]

                vote_count = all_votes.count(group_id)

                group_stats.append({
                    "group_id": group_id,
                    "group_name": group_name,
                    "vote_count": vote_count
                })

    except sqlite3.Error as e:
        logging.error(f"Error downloading group vote stats: {e}")
        return jsonify({"success": False, "message": "無法下載各組投票統計"}), 500

    # 轉成 Excel
    df = pd.DataFrame(group_stats)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Group_Votes")
    output.seek(0)

    return send_file(output,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True,
                     download_name="各組投票統計.xlsx")


@app.route("/admin/feedbacks")
def admin_feedbacks():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT f.student_id, s.student_name, s.student_class, f.group_id, g.name, f.feedback, 
                       f.feedback_date, f.feedback_time
                FROM feedbacks f
                LEFT JOIN students s ON f.student_id = s.student_id
                LEFT JOIN groups g ON f.group_id = g.id
                ORDER BY f.timestamp DESC
            ''')
            rows = c.fetchall()
            logging.info(f"Fetched {len(rows)} feedback records for admin page.")
            c.execute("SELECT DISTINCT group_id FROM feedbacks WHERE group_id NOT IN (SELECT id FROM groups)")
            invalid_groups = [row[0] for row in c.fetchall()]
            if invalid_groups:
                logging.warning(f"Invalid group_ids found in feedbacks: {invalid_groups}")
    except sqlite3.OperationalError as e:
        logging.error(f"Error querying feedbacks: {e}")
        return render_template("admin_feedbacks.html", feedbacks=[], message="無法載入回饋資料")

    feedbacks = []
    for row in rows:
        feedbacks.append({
            "studentId": row[0],
            "studentName": row[1] or "未知學生",
            "studentClass": row[2] or "未知班級",
            "groupId": row[3],
            "group_name": row[4] or "未知組別",
            "feedback": row[5],
            "feedback_date": row[6] or "N/A",
            "feedback_time": row[7] or "N/A"
        })

    if not feedbacks:
        logging.info("No feedback records found for admin page.")
        return render_template("admin_feedbacks.html", feedbacks=[], message="目前沒有回饋資料")

    return render_template("admin_feedbacks.html", feedbacks=feedbacks)

@app.route('/api/admin/feedbacks', methods=['GET'])
def get_feedbacks():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT f.student_id, s.student_name, s.student_class, f.group_id, g.name, f.feedback, 
                       f.feedback_date, f.feedback_time
                FROM feedbacks f
                LEFT JOIN students s ON f.student_id = s.student_id
                LEFT JOIN groups g ON f.group_id = g.id
            ''')
            feedbacks = c.fetchall()
            logging.info(f"Fetched {len(feedbacks)} feedback records for API.")
            c.execute("SELECT DISTINCT group_id FROM feedbacks WHERE group_id NOT IN (SELECT id FROM groups)")
            invalid_groups = [row[0] for row in c.fetchall()]
            if invalid_groups:
                logging.warning(f"Invalid group_ids found in feedbacks: {invalid_groups}")
    except sqlite3.Error as e:
        logging.error(f"Error fetching feedbacks for API: {e}")
        return jsonify({"success": False, "message": "無法獲取回饋資料"}), 500

    feedback_data = []
    for feedback in feedbacks:
        feedback_data.append({
            'studentId': feedback[0],
            'studentName': feedback[1] or '未知學生',
            'studentClass': feedback[2] or '未知班級',
            'groupId': feedback[3],
            'groupName': feedback[4] or '未知組別',
            'feedback': feedback[5],
            'feedbackDate': feedback[6] or 'N/A',
            'feedbackTime': feedback[7] or 'N/A'
        })

    if not feedback_data:
        logging.info("No feedback records found for API.")
        return jsonify({"success": True, "feedbacks": [], "message": "目前沒有回饋資料"})

    return jsonify({"success": True, "feedbacks": feedback_data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)