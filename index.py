from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# 資料庫路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "database.db")
GROUPS_FILE = os.path.join(BASE_DIR, "data", "groups.json")


# 初始化資料庫
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
              CREATE TABLE IF NOT EXISTS students
              (
                  student_id
                  TEXT
                  PRIMARY
                  KEY,
                  student_name
                  TEXT
                  NOT
                  NULL,
                  has_voted
                  INTEGER
                  DEFAULT
                  0
              )
              ''')
    c.execute('''
              CREATE TABLE IF NOT EXISTS votes
              (
                  student_id
                  TEXT,
                  group_id
                  TEXT,
                  vote_time
                  TEXT, -- 新增這一欄位來記錄投票時間
                  PRIMARY
                  KEY
              (
                  student_id,
                  group_id
              )
                  )
              ''')
    conn.commit()
    conn.close()


init_db()


def get_votes_by_student(student_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT group_id, vote_time FROM votes WHERE student_id = ?", (student_id,))
    votes = [{"group_id": row[0], "vote_time": row[1]} for row in c.fetchall()]
    conn.close()
    return votes


def load_groups():
    import json
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    student_id = request.form["student_id"]
    student_name = request.form["student_name"]

    if len(student_id) != 9 or not student_id.isdigit():
        return render_template("index.html", message="請輸入正確學號。")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT has_voted FROM students WHERE student_id = ?", (student_id,))
    row = c.fetchone()

    if row:
        if row[0] == 1:
            return render_template("index.html", message="此學號已投票，不得重複投票。")
        else:
            # 尚未完成投票，直接讓他重新登入投票
            session["student_id"] = student_id
            session["votes"] = get_votes_by_student(student_id)
            return redirect(url_for("vote_page"))

    c.execute("INSERT INTO students (student_id, student_name) VALUES (?, ?)", (student_id, student_name))
    conn.commit()
    conn.close()

    session["student_id"] = student_id
    session["votes"] = []

    return redirect(url_for("vote_page"))


@app.route("/vote")
def vote_page():
    student_id = session.get("student_id")
    if not student_id:
        return redirect(url_for("index"))

    votes = get_votes_by_student(student_id)
    if len(votes) >= 3:
        return redirect(url_for("succeed"))

    groups = load_groups()
    session["votes"] = votes
    return render_template("vote.html", groups=groups)


@app.route("/api/vote", methods=["POST"])
def vote():
    if "student_id" not in session:
        return jsonify({"success": False, "message": "未登入，請先註冊學號"}), 401

    student_id = session["student_id"]
    data = request.get_json()
    group_id = data.get("group_id")

    if not group_id:
        return jsonify({"success": False, "message": "缺少組別 ID"}), 400

    print(f"接收到的資料: {data}")  # 用來檢查接收到的資料

    votes = get_votes_by_student(student_id)
    if group_id in [v["group_id"] for v in votes]:
        return jsonify({"success": False, "message": "您已經投過此組別！"}), 403
    if len(votes) >= 3:
        return jsonify({"success": False, "message": "您已經投過三票了！"}), 403

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 取得當前時間
    vote_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("INSERT INTO votes (student_id, group_id, vote_time) VALUES (?, ?, ?)", (student_id, group_id, vote_time))
    conn.commit()
    conn.close()

    votes.append({"group_id": group_id, "vote_time": vote_time})
    session["votes"] = votes

    return jsonify({"success": True})


@app.route("/api/vote/confirm", methods=["POST"])
def confirm_vote():
    if "student_id" not in session or "votes" not in session:
        return jsonify({"success": False, "message": "尚未完成投票"}), 400

    student_id = session["student_id"]

    # 更新 has_voted 為 1，表示此學生已完成投票
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE students SET has_voted = 1 WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()

    session.pop("votes", None)
    return jsonify({"success": True})


@app.route("/api/toggle_vote", methods=["POST"])
def toggle_vote():
    if "student_id" not in session:
        return jsonify({"success": False, "message": "未登入"}), 401

    student_id = session["student_id"]
    data = request.get_json()
    group_id = data.get("group_id")

    if not group_id:
        return jsonify({"success": False, "message": "缺少組別 ID"}), 400

    votes = get_votes_by_student(student_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if group_id in [v["group_id"] for v in votes]:
        c.execute("DELETE FROM votes WHERE student_id = ? AND group_id = ?", (student_id, group_id))
        message = "已取消投票"
        voted = False
    else:
        if len(votes) >= 3:
            conn.close()
            return jsonify({"success": False, "message": "最多只能投三票"}), 403

        # 取得當前時間
        vote_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute("INSERT INTO votes (student_id, group_id, vote_time) VALUES (?, ?, ?)",
                  (student_id, group_id, vote_time))
        message = "投票成功"
        voted = True

    conn.commit()
    conn.close()

    session["votes"] = get_votes_by_student(student_id)

    return jsonify({"success": True, "message": message, "voted": voted, "vote_count": len(session['votes'])})


@app.route("/succeed")
def succeed():
    return render_template("succeed.html")


@app.route("/admin")
def admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 所有學生及他們的投票
    c.execute("SELECT student_id, student_name FROM students")
    students_raw = c.fetchall()

    student_votes = {}
    for student_id, name in students_raw:
        c.execute("SELECT group_id, vote_time FROM votes WHERE student_id = ?", (student_id,))
        group_votes = [{"group_id": row[0], "vote_time": row[1]} for row in c.fetchall()]
        student_votes[student_id] = {"name": name, "votes": group_votes}

    # 每組的投票總數
    c.execute("SELECT group_id, COUNT(*) FROM votes GROUP BY group_id")
    vote_counts = c.fetchall()

    conn.close()

    return render_template("admin.html", students=student_votes, vote_counts=vote_counts)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
