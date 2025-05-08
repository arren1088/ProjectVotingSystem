from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 替換為你自己的密鑰

# 資料檔案路徑
STUDENTS_FILE = "data/students.json"
VOTES_FILE = "data/votes.json"
GROUPS_FILE = "data/groups.json"


# 載入學生資料
def load_students():
    if os.path.exists(STUDENTS_FILE):
        with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# 儲存學生資料
def save_student(student_id, student_name):
    students = load_students()

    # 儲存學生資料，結構是 {student_id: {"name": student_name, "votes": []}}
    students[student_id] = {"name": student_name, "votes": []}

    # 儲存回 JSON 檔案
    with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(students, f, ensure_ascii=False, indent=2)


# 儲存學生投票
def save_student_votes(student_id, votes):
    students = load_students()

    # 更新學生投票資料
    if student_id in students:
        students[student_id]["votes"] = votes
    else:
        students[student_id] = {"votes": votes}

    # 儲存回 JSON 檔案
    with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(students, f, ensure_ascii=False, indent=2)


# 儲存票數
def save_vote(group_id):
    if not os.path.exists(VOTES_FILE):
        votes = {}
    else:
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            votes = json.load(f)
    votes[group_id] = votes.get(group_id, 0) + 1
    with open(VOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(votes, f, ensure_ascii=False, indent=2)


# 載入組別資料
def load_groups():
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

    # 檢查學號長度是否為9碼
    if len(student_id) != 9 or not student_id.isdigit():
        return render_template("index.html", message="請輸入正確學號。")

    students = load_students()

    # 檢查學號是否已存在
    if student_id in students:
        return render_template("index.html", message="學號已投票，不得重複投票。")

    # 如果學生已存在且已投超過三票就導向成功頁
    if student_id in students and len(students[student_id]["votes"]) >= 3:
        return redirect(url_for("succeed"))

    # 儲存學號和姓名到 JSON 檔案
    save_student(student_id, student_name)

    # 儲存學號到 session
    session["student_id"] = student_id
    session["votes"] = students.get(student_id, {}).get("votes", [])

    return redirect(url_for("vote_page"))


@app.route("/vote")
def vote_page():
    student_id = session.get("student_id")
    if not student_id:
        return redirect(url_for("index"))

    if len(session.get("votes", [])) >= 3:
        return redirect(url_for("succeed"))

    groups = load_groups()
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

    students = load_students()
    votes = students.get(student_id, {}).get("votes", [])

    if group_id in votes:
        return jsonify({"success": False, "message": "您已經投過此組別！"}), 403
    if len(votes) >= 3:
        return jsonify({"success": False, "message": "您已經投過三票了！"}), 403

    votes.append(group_id)
    save_student_votes(student_id, votes)
    session["votes"] = votes

    return jsonify({"success": True})


@app.route("/api/vote/confirm", methods=["POST"])
def confirm_vote():
    if "student_id" not in session or "votes" not in session:
        return jsonify({"success": False, "message": "尚未完成投票"}), 400

    student_id = session["student_id"]
    votes = session["votes"]

    # 更新 votes.json 統計每一組的票數
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            vote_counts = json.load(f)
    else:
        vote_counts = {}

    for group_id in votes:
        vote_counts[group_id] = vote_counts.get(group_id, 0) + 1

    with open(VOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(vote_counts, f, ensure_ascii=False, indent=2)

    # 清除 session 中的票數（防止重複送出）
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

    students = load_students()
    votes = students.get(student_id, {}).get("votes", [])

    if group_id in votes:
        # 取消投票
        votes.remove(group_id)
        message = "已取消投票"
        voted = False
    else:
        if len(votes) >= 3:
            return jsonify({"success": False, "message": "最多只能投三票"}), 403
        votes.append(group_id)
        message = "投票成功"
        voted = True

    # 存回
    save_student_votes(student_id, votes)
    session["votes"] = votes

    return jsonify({"success": True, "message": message, "voted": voted, "vote_count": len(votes)})



@app.route("/succeed")
def succeed():
    return render_template("succeed.html")


if __name__ == "__main__":
    app.run(debug=True)
